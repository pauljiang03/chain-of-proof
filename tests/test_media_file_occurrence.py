"""Native FAT/exFAT byte fixtures bind time pairs to physical directory records."""
import io
import json
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

from dissect.fat.c_exfat import c_exfat
from dissect.target.filesystems.exfat import ExfatFilesystem
from dissect.target.filesystems.fat import FatFilesystem
from dissect.target.volume import Volume
from dissect.util.stream import RangeStream, RunlistStream

from checker.check import check
from checker.facts import JsonFacts, file_occurrence
from extractor import acquisition, media
from extractor.fatcarve import parse_directory
from extractor.source_scope import base_volume_scope
from extractor.store import Evidence
from verifier.verify import verify


COMMON = dict(image="fixture.img", exhibit="Synthetic media", **base_volume_scope())
DATE = ((2020 - 1980) << 9) | (1 << 5) | 2
OLD_DATE = ((2019 - 1980) << 9) | (1 << 5) | 2
TIME = (3 << 11) | (4 << 5) | 3


class Disk(io.BytesIO):
    def __init__(self, raw):
        super().__init__(raw)
        self.size = len(raw)


def short_entry(name=b"A       TXT", *, cluster=0, attr=0x20, deleted=False):
    raw = bytearray(32)
    raw[:11] = name
    raw[11] = attr
    raw[13] = 7
    struct.pack_into("<HH", raw, 14, TIME, DATE)
    struct.pack_into("<HH", raw, 22, TIME, OLD_DATE)
    struct.pack_into("<H", raw, 26, cluster)
    if deleted:
        raw[0] = 0xE5
    return bytes(raw)


def long_entry(name="Long file.txt"):
    raw = bytearray(b"\xff" * 32)
    raw[0], raw[11], raw[12], raw[13] = 0x41, 0x0F, 0, 0
    raw[26:28] = b"\x00\x00"
    text = (name + "\x00").encode("utf-16-le")[:26].ljust(26, b"\xff")
    raw[1:11], raw[14:26], raw[28:32] = text[:10], text[10:22], text[22:26]
    return bytes(raw)


def fat_image(records):
    raw = bytearray(128 * 512)
    raw[:11] = b"\xeb\x3c\x90MSDOS5.0"
    struct.pack_into("<HBHBHHBHHHII", raw, 11,
                     512, 1, 1, 1, 16, 128, 0xF8, 1, 1, 1, 0, 0)
    raw[36:39] = b"\x80\x00\x29"
    struct.pack_into("<I", raw, 39, 0xDEADBEEF)
    raw[43:54] = b"TEST       "
    raw[54:62] = b"FAT12   "
    raw[510:512] = b"\x55\xaa"
    raw[512:515] = b"\xf8\xff\xff"
    for index, record in enumerate(records):
        raw[1024 + index * 32:1056 + index * 32] = record
    return raw


def exfat_entry(name="a.txt", *, cluster=0, directory=False, size=0):
    metadata = c_exfat.FILE_DIRECTORY_ENTRY(
        entry_type=0x85, subentry_count=2,
        attributes=c_exfat.ATTRIBUTES(directory=int(directory)),
        create_time=(DATE << 16) | TIME, modified_time=(OLD_DATE << 16) | TIME,
        access_time=(DATE << 16) | TIME,
        create_timezone=0x80, modified_timezone=0x80, access_timezone=0x80)
    stream = c_exfat.STREAM_DIRECTORY_ENTRY(
        entry_type=0xC0, flags=c_exfat.FILE_FLAGS(not_fragmented=1),
        filename_length=len(name), location=cluster, data_length=size)
    filename = c_exfat.FILENAME_DIRECTORY_ENTRY(entry_type=0xC1, filename=name.ljust(15, "\x00"))
    return metadata.dumps() + stream.dumps() + filename.dumps()


def exfat_image(records, *, cluster_exp=2):
    raw = bytearray(32 * 512)
    header = c_exfat.EXFAT_HEADER(
        fs_name=b"EXFAT   ", volume_sector_count=32, fat_sector=1,
        fat_sector_count=1, cluster_heap_sector=2, cluster_heap_count=6,
        root_dir_cluster=2, volume_serial=0xDEADBEEF,
        bytes_per_sector_exp=9, sectors_per_cluster_exp=cluster_exp,
        number_of_fats=1, boot_signature=0xAA55)
    raw[:512] = header.dumps()
    struct.pack_into("<I", raw, 512 + 2 * 4, 0xFFFFFFFF)
    label = c_exfat.VOLUME_DIRECTORY_ENTRY(entry_type=0x83, label_length=4,
                                         volume_label="TEST".ljust(11, "\x00")).dumps()
    body = label + b"".join(records)
    raw[1024:1024 + len(body)] = body
    return raw


def target_for(images, kind="fat", *, offsets=None, disk_index=0):
    offsets = offsets or [4096 + index * 131072 for index in range(len(images))]
    disk = Disk(bytes(max(offset + len(raw) for offset, raw in zip(offsets, images))))
    volumes = []
    for index, (offset, raw) in enumerate(zip(offsets, images)):
        disk.seek(offset)
        disk.write(raw)
        vs = NS(__type__="disk", fh=disk, disk=disk)
        vol = Volume(RangeStream(disk, offset, len(raw)), index + 1, offset,
                     len(raw), None, None, disk=disk, vs=vs)
        vol.fs = (FatFilesystem if kind == "fat" else ExfatFilesystem)(vol)
        volumes.append(vol)
    return NS(disks=[Disk(bytes(512)) for _ in range(disk_index)] + [disk], volumes=volumes)


def extract(target):
    evidence = Evidence()
    with patch.object(media.Target, "open", return_value=target):
        media.extract_media(evidence, Path(COMMON["image"]), {"exhibit": COMMON["exhibit"]},
                            "UTC", 42, "real synthetic filesystem parser",
                            acquisition=acquisition.fallback(COMMON["image"], COMMON["exhibit"]))
    return evidence


def time_rows(evidence):
    return [(row, json.loads(row[5])) for row in evidence.rows()
            if row[0] in ("fileCreated", "fileModified")]


class MediaFileOccurrence(unittest.TestCase):
    def test_fat_empty_files_use_distinct_short_entry_slots_not_cluster_zero(self):
        target = target_for([fat_image([short_entry(), short_entry(b"B       TXT")])], disk_index=1)
        evidence = extract(target)
        self.assertEqual(evidence.problems, [])
        rows = time_rows(evidence)
        self.assertEqual(len(rows), 4)
        for row, prov in rows:
            occurrence = prov["file_occurrence"]
            self.assertEqual(set(occurrence), {"schema_version", "disk_index", "partition_offset_bytes",
                                               "partition_size_bytes", "entry_kind", "entry_id"})
            self.assertEqual(occurrence["disk_index"], 1)
            self.assertEqual(occurrence["partition_offset_bytes"], 4096)
            self.assertEqual(occurrence["entry_kind"], "fat_directory_entry")
            self.assertEqual(occurrence["entry_id"], 1024 if row[3] == r"\A.TXT" else 1056)
            self.assertIsNotNone(file_occurrence(prov))
        self.assertEqual({p["file_occurrence"]["entry_id"] for _, p in rows}, {1024, 1056})

    def test_long_names_deleted_slots_and_volume_label_do_not_shift_native_offset(self):
        records = [short_entry(deleted=True), short_entry(b"LABEL      ", attr=8),
                   long_entry(), short_entry(b"LONGFI~1TXT")]
        target = target_for([fat_image(records)])
        slots = media._directory_occurrences(target.volumes[0], target.volumes[0].fs, "/")
        self.assertEqual(slots[records[-1]], 1120)
        self.assertNotIn(records[0], slots)
        native = target.volumes[0].fs.get("/Long file.txt")
        self.assertEqual(slots[media._native_key(native, "fat")], 1120)

    def test_exfat_primary_entry_offset_uses_sector_units_and_empty_files_are_distinct(self):
        target = target_for([exfat_image([exfat_entry(), exfat_entry("b.txt")])], "exfat")
        evidence = extract(target)
        self.assertEqual(evidence.problems, [])
        rows = time_rows(evidence)
        self.assertEqual(len(rows), 4)
        self.assertEqual({p["file_occurrence"]["entry_id"] for _, p in rows}, {1056, 1152})
        self.assertTrue(all(p["file_occurrence"]["entry_kind"] == "exfat_directory_entry" for _, p in rows))
        self.assertTrue(all(file_occurrence(p) is not None for _, p in rows))

    def test_exfat_subdirectory_maps_back_to_partition_not_its_own_stream(self):
        image = exfat_image([exfat_entry("folder", cluster=3, directory=True, size=2048)])
        image[3072:3168] = exfat_entry()
        target = target_for([image], "exfat")
        evidence = extract(target)
        self.assertEqual(evidence.problems, [])
        rows = time_rows(evidence)
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row[3] == r"\folder\a.txt" for row, _ in rows))
        self.assertEqual({p["file_occurrence"]["entry_id"] for _, p in rows}, {3072})

    def test_real_fat_fragmented_directory_keeps_second_run_physical_slot(self):
        image = fat_image([short_entry(b"FOLDER     ", cluster=2, attr=16)])
        # FAT12 cluster 2 -> cluster 4 -> end of chain, with cluster 3 skipped.
        image[515:517] = b"\x04\x00"
        image[518:520] = b"\xff\x0f"
        image[1536:2048] = short_entry(deleted=True) * 16
        image[1536:1568] = short_entry(b".          ", cluster=2, attr=16)
        image[1568:1600] = short_entry(b"..         ", attr=16)
        image[2560:2592] = short_entry()
        evidence = extract(target_for([image]))
        self.assertEqual(evidence.problems, [])
        rows = time_rows(evidence)
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row[3] == r"\FOLDER\A.TXT" for row, _ in rows))
        self.assertEqual({p["file_occurrence"]["entry_id"] for _, p in rows}, {2560})

    def test_duplicate_native_bytes_are_ambiguous_in_both_filesystems(self):
        for kind, make_image, record in (("fat", fat_image, short_entry()),
                                        ("exfat", exfat_image, exfat_entry())):
            with self.subTest(kind=kind):
                evidence = extract(target_for([make_image([record, record])], kind))
                self.assertTrue(evidence.problems)
                self.assertTrue(time_rows(evidence))
                self.assertTrue(all("file_occurrence" not in p for _, p in time_rows(evidence)))

    def test_partition_and_disk_context_fail_closed(self):
        changes = [lambda t, v: setattr(v, "offset", -1),
                   lambda t, v: setattr(v, "size", 0),
                   lambda t, v: setattr(v, "disk", Disk(bytes(4096))),
                   lambda t, v: t.disks.append(v.disk),
                   lambda t, v: setattr(v.vs, "__type__", "lvm"),
                   lambda t, v: setattr(v.fh, "offset", v.offset + 1)]
        for change in changes:
            target = target_for([fat_image([short_entry()])])
            change(target, target.volumes[0])
            with self.assertRaises(ValueError):
                media._partition_context(target, target.volumes[0], COMMON)
        target = target_for([fat_image([short_entry()])])
        for name in ("image", "exhibit", "source_snapshot", "source_variant"):
            for value in (None, "", "unknown", "none", "(none)", " padded ", "bad\nvalue", "x" * 513):
                with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                    media._partition_context(target, target.volumes[0], dict(COMMON, **{name: value}))

    def test_fragmented_directory_mapping_and_bounded_failure_controls(self):
        volume = NS(size=8192)
        data = RangeStream(volume, 1024, 7168)
        stream = RunlistStream(data, [(1, 1), (7, 1)], 1024, 512)
        locate = media._stream_locator(stream, volume)
        self.assertEqual(locate(32), 1568)
        self.assertEqual(locate(544), 4640)
        for bad in (RunlistStream(data, [(None, 1)], 512, 512),
                    RunlistStream(data, [(15, 1)], 512, 512),
                    RunlistStream(data, [(1, 1)], 1024, 512)):
            with self.assertRaises(ValueError):
                media._stream_locator(bad, volume)
        cycle = RangeStream(volume, 0, 8192)
        cycle._fh = cycle
        with self.assertRaises(ValueError):
            media._stream_locator(cycle, volume)
        with self.assertRaises(ValueError):
            media._read_directory(NS(size=media._MAX_DIRECTORY_BYTES + 32))
        with self.assertRaises(ValueError):
            list(media._record_slots(exfat_entry()[:-32], "exfat"))
        with self.assertRaises(ValueError):
            locate(1000)

    def test_recovered_deleted_and_lfn_entries_keep_physical_slots_and_variant(self):
        raw = bytearray(512)
        records = [short_entry(b".          ", attr=16, cluster=2),
                   short_entry(b"..         ", attr=16), short_entry(b"LABEL      ", attr=8),
                   long_entry(), short_entry(b"LONGFI~1TXT", deleted=True), short_entry(b"B       TXT")]
        raw[:len(records) * 32] = b"".join(records)
        parsed = parse_directory(raw)
        self.assertEqual(media._recovered_slots(raw, parsed), [128, 160])
        image = bytearray(4096)
        image[1024:1536] = raw
        vol = io.BytesIO(image)
        fs = NS(fatfs=NS(bpb=NS(BPB_RootEntCnt=0, BPB_BytsPerSec=512, BPB_SecPerClus=1,
                               BPB_RsvdSecCnt=1, BPB_NumFATs=1, BPB_TotSec32=8),
                        bpb_ext=NS(BPB_FATSz32=1)))
        context = dict(schema_version=1, disk_index=0, partition_offset_bytes=4096,
                       partition_size_bytes=4096)
        evidence = Evidence()
        with patch.object(media, "carve_fat32", return_value={2: parsed}):
            media._recovered_entries(evidence, vol, fs, acquisition.fallback("fixture.img", "Synthetic media"),
                                     ZoneInfo("UTC"), 42, COMMON, context)
        self.assertEqual(evidence.problems, [])
        rows = time_rows(evidence)
        self.assertEqual(len(rows), 4)
        self.assertEqual({p["file_occurrence"]["entry_id"] for _, p in rows}, {1152, 1184})
        self.assertEqual({p["source_variant"] for _, p in rows}, {"unallocated-recovery"})
        self.assertTrue(all(file_occurrence(p) is not None for _, p in rows))
        raw[160] = ord("C")
        with self.assertRaises(ValueError):
            media._recovered_slots(raw, parsed)

    def test_actual_reader_rows_certify_and_cross_partition_join_fails(self):
        raw = fat_image([short_entry()])
        evidence = extract(target_for([raw, raw]))
        self.assertEqual(evidence.problems, [])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence.write_json(root / "facts.json", {"fixture": "synthetic FAT12 directory bytes"})
            facts = JsonFacts(root / "facts.json")
            created = sorted((f for f in facts.all() if f.kind == "fileCreated"),
                             key=lambda f: f.prov["file_occurrence"]["partition_offset_bytes"])
            modified = sorted((f for f in facts.all() if f.kind == "fileModified"),
                              key=lambda f: f.prov["file_occurrence"]["partition_offset_bytes"])
            self.assertEqual(len(created), 2)
            positive = check({"copiedHere": [created[0].id, modified[0].id]}, "MediaOccurrence", facts, out_dir=root)
            self.assertEqual(positive["status"], "verified", positive)
            self.assertEqual(verify(positive, facts), [])
            self.assertIn("does not establish a copying action", positive["english"])
            negative = check({"copiedHere": [created[0].id, modified[1].id]}, "MediaPartitionCollision", facts, out_dir=root)
            self.assertEqual(negative["status"], "rejected", negative)
            self.assertTrue(any(line.startswith("FAIL sameFileOccurrence")
                                for line in negative["parts"][0]["bricks"]))


if __name__ == "__main__":
    unittest.main()
