"""Exact historical identity and byte-origin controls using parser fixtures."""
import copy
import hashlib
import io
import json
import struct
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch
from uuid import UUID

from extractor import historical_sources as h
from extractor import optical
from tests.test_optical import make_disc


COPY = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
STORE = UUID("11111111-2222-3333-4444-555555555555")
SET = UUID("99999999-2222-3333-4444-555555555555")
VOLUME = UUID("22222222-3333-4444-5555-666666666666")
FT = 130717690472938055
SERIAL = 0x123456789ABCDEF0
COMMON = dict(image="fixture.E01", exhibit="PC", source_snapshot="base-volume", source_variant="primary")
PATH = r"C:\folder\same.txt"


def store(copy_id=COPY, *, store_id=STORE, created=FT):
    return NS(copy_identifier=copy_id, copy_set_identifier=SET,
              desc2=NS(store_identifier=store_id.bytes_le, creation_time=created),
              desc3=NS(store_identifier=store_id.bytes_le, store_header_offset=0xC000),
              creation_time=created, open=Mock(side_effect=lambda: io.BytesIO(b"snapshot")))


def parsed(stores):
    return NS(volume_identifier=VOLUME, store_volume_identifier=VOLUME,
              header=NS(catalog_offset=0x4000), catalog=NS(stores=stores))


def filesystem(serial=SERIAL):
    return NS(__type__="ntfs", ntfs=NS(serial=serial), volume=io.BytesIO(b"base"))


class Record:
    def __init__(self, data=b"same", *, children=None, deleted=False, reparse=False,
                 stamp=FT, sequence=4, segment=40, stream_error=None, declared_size=None):
        self.data, self.children = data, children
        self.header = NS(Flags=0 if deleted else 1, SequenceNumber=sequence)
        self.segment, self.reparse, self.stream_error = segment, reparse, stream_error
        self.declared_size = len(data) if declared_size is None else declared_size
        self.attributes = NS(STANDARD_INFORMATION=NS(attr=NS(CreationTime=stamp,
            LastModificationTime=stamp, LastChangeTime=stamp, LastAccessTime=stamp)))
        self.opened = 0

    def is_reparse_point(self):
        return self.reparse

    def is_dir(self):
        return self.children is not None

    def is_file(self):
        return not self.is_dir()

    def index(self, name):
        assert name == "$I30"
        return NS(search=self.search)

    def search(self, name):
        record = self.children[name.casefold()]
        if isinstance(record, Exception):
            raise record
        sequence = getattr(record, "index_sequence", record.header.SequenceNumber)
        ref = NS(SegmentNumberLowPart=record.segment, SegmentNumberHighPart=0, SequenceNumber=sequence)
        return NS(dereference=lambda: record, header=NS(FileReference=ref))

    def size(self):
        return self.declared_size

    def open(self):
        self.opened += 1
        if self.stream_error:
            raise self.stream_error
        return io.BytesIO(self.data)


def ntfs(record=None, *, serial=SERIAL, parent_reparse=False):
    folder = Record(children={} if record is None else {"same.txt": record}, reparse=parent_reparse)
    return NS(serial=serial, mft=NS(root=Record(children={"folder": folder})))


def inventory(stores=None, limits=None, fs=None):
    fs = fs or filesystem()
    target = NS(filesystems=[fs], fs=NS(mounts={"c:": fs}))
    with patch.object(h, "_parse_vss", return_value=parsed(stores if stores is not None else [store()])):
        return h.discover_vss(target, COMMON, limits=limits)


def compare(base, snapshot, *, inv=None, paths=None):
    inv = inv or inventory()
    with patch.object(h, "_open_ntfs", side_effect=[base, snapshot]):
        return h.compare_versions(inv, COPY, paths or [PATH])


class SourceInventoryTests(unittest.TestCase):
    def test_catalog_metadata_does_not_open_or_claim_snapshot_content(self):
        selected = store()
        common_before = copy.deepcopy(COMMON)
        inv = inventory([selected])
        self.assertTrue(inv.complete)
        meta = inv.as_dict()["sources"][0]
        selected.open.assert_not_called()
        self.assertEqual(meta["snapshot_id"], "vss:" + str(COPY))
        self.assertEqual((meta["store_uuid"], meta["set_uuid"]), (str(STORE), str(SET)))
        self.assertEqual(meta["created_at"], "2015-03-25T14:57:27.2938055Z")
        self.assertEqual(meta["creation_filetime"], FT)
        self.assertEqual(meta["provenance"]["source_snapshot"], "base-volume")
        self.assertEqual(meta["volume"]["ntfs_volume_serial"], "123456789ABCDEF0")
        self.assertEqual(meta["volume"]["vss_volume_uuid"], str(VOLUME))
        self.assertEqual(COMMON, common_before)
        meta["provenance"]["source_snapshot"] = "changed"
        self.assertEqual(inv.sources[0].metadata["provenance"]["source_snapshot"], "base-volume")
        json.dumps(inv.as_dict())

    def test_selection_uses_exact_copy_not_time_store_or_set_identifier(self):
        older = store(UUID(int=3), store_id=UUID(int=7), created=FT - 10)
        inv = inventory([store(), older])
        self.assertEqual(h.select_vss(inv, "vss:{" + str(COPY).upper() + "}").metadata["copy_uuid"], str(COPY))
        self.assertEqual(h.select_vss(inv, UUID(int=3)).metadata["creation_filetime"], FT - 10)
        for wrong in (None, "latest", "earliest", "2015-03-25", str(STORE), str(SET), "vss:invalid"):
            with self.subTest(wrong=wrong), self.assertRaises(h.SourceSelectionError):
                h.select_vss(inv, wrong)

    def test_duplicate_copy_needs_unique_volume_identity(self):
        left, right = filesystem(), filesystem(SERIAL + 1)
        target = NS(filesystems=[left, right], fs=NS(mounts={"c:": left, "d:": right}))
        with patch.object(h, "_parse_vss", side_effect=[parsed([store()]), parsed([store()])]):
            inv = h.discover_vss(target, COMMON)
        with self.assertRaises(h.SourceSelectionError):
            h.select_vss(inv, COPY)
        identity = inv.sources[0].metadata["volume"]["volume_identity"]
        self.assertEqual(h.select_vss(inv, COPY, volume_identity=identity).metadata["volume"]["volume_identity"], identity)
        duplicate = inventory([store(), store()])
        with self.assertRaises(h.SourceSelectionError):
            h.select_vss(duplicate, COPY, volume_identity=duplicate.sources[0].metadata["volume"]["volume_identity"])

    def test_mixed_unknown_or_missing_origins_are_not_upgraded(self):
        fs = filesystem()
        target = NS(filesystems=[fs], fs=NS(mounts={"c:": fs}))
        for changes in ({"source_snapshot": "unknown"}, {"source_snapshot": "vss:" + str(COPY)},
                        {"source_variant": None}, {"image": ""}, {"exhibit": None}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                h.discover_vss(target, dict(COMMON, **changes))

    def test_absent_catalog_unreadable_and_unsupported_are_distinct(self):
        for parsed_value, status, complete in ((None, "absent", True), (OSError("broken"), "unreadable", False),
                                               (NotImplementedError("layout"), "unsupported", False)):
            fs = filesystem()
            target = NS(filesystems=[fs], fs=NS(mounts={"c:": fs}))
            effect = {"side_effect": parsed_value} if isinstance(parsed_value, Exception) else {"return_value": parsed_value}
            with patch.object(h, "_parse_vss", **effect):
                inv = h.discover_vss(target, COMMON)
            self.assertEqual(inv.volumes[0]["status"], status)
            self.assertEqual(inv.complete, complete)

    def test_incomplete_discovery_cannot_hide_duplicate_candidates(self):
        inv = inventory([store(), store(UUID(int=2))], h.Limits(max_sources=1))
        self.assertFalse(inv.complete)
        self.assertEqual(inv.issues[0]["status"], "limit_exceeded")
        with self.assertRaises(h.SourceSelectionError):
            h.select_vss(inv, COPY)

    def test_non_ntfs_target_is_unsupported_and_volume_limit_is_incomplete(self):
        inv = h.discover_vss(NS(filesystems=[NS(__type__="fat")], fs=NS(mounts={})), COMMON)
        self.assertFalse(inv.complete)
        self.assertEqual(inv.issues[0]["status"], "unsupported")
        left, right = filesystem(), filesystem(SERIAL + 1)
        with patch.object(h, "_parse_vss", return_value=parsed([store()])):
            inv = h.discover_vss(NS(filesystems=[left, right], fs=NS(mounts={"c:": left, "d:": right})),
                                 COMMON, limits=h.Limits(max_volumes=1))
        self.assertFalse(inv.complete)
        self.assertEqual(inv.issues[-1]["status"], "limit_exceeded")

    def test_linked_descriptor_mismatch_and_invalid_time_fail(self):
        wrong = store()
        wrong.desc3.store_identifier = UUID(int=99).bytes_le
        for selected in (wrong, store(created=True), store(created=-1), store(created=2**64)):
            inv = inventory([selected])
            self.assertFalse(inv.complete)
            self.assertFalse(inv.sources)


class ComparisonTests(unittest.TestCase):
    def test_actual_bytes_override_equal_sizes_and_times(self):
        report = compare(ntfs(Record(b"new!")), ntfs(Record(b"old!")))
        item = report["paths"][0]
        self.assertEqual(item["comparison"], "different_content")
        self.assertEqual(item["base"]["sha256"], hashlib.sha256(b"new!").hexdigest())
        self.assertEqual(item["snapshot"]["sha256"], hashlib.sha256(b"old!").hexdigest())
        self.assertEqual(item["base"]["provenance"]["source_snapshot"], "base-volume")
        self.assertEqual(item["snapshot"]["provenance"]["source_snapshot"], "vss:" + str(COPY))
        self.assertEqual(report["selected_source"]["provenance"]["source_snapshot"], "base-volume")
        self.assertEqual(item["base"]["stat"]["mft_sequence"], 4)
        self.assertEqual(item["snapshot"]["stat"]["timestamps_filetime"]["created"], FT)
        self.assertEqual(report["usage"]["content_bytes"], 8)
        json.dumps(report)

    def test_time_changes_do_not_create_a_content_change_or_direction_claim(self):
        report = compare(ntfs(Record(b"x", stamp=FT + 10)), ntfs(Record(b"x", stamp=FT - 10)))
        self.assertEqual(report["paths"][0]["comparison"], "same_content")
        self.assertNotIn("actor", report["paths"][0])
        self.assertNotIn("direction", report["paths"][0])

    def test_absent_unreadable_and_unsupported_content_are_distinct(self):
        snapshot = ntfs(Record(b"old"))
        cases = [(ntfs(), "absent"), (ntfs(Record(stream_error=OSError("access"))), "unreadable"),
                 (ntfs(Record(deleted=True)), "unsupported"), (ntfs(Record(reparse=True)), "unsupported"),
                 (ntfs(Record(), parent_reparse=True), "unsupported")]
        for base, expected in cases:
            with self.subTest(expected=expected):
                item = compare(base, snapshot)["paths"][0]
                self.assertEqual(item["base"]["status"], expected)
                self.assertEqual(item["snapshot"]["status"], "present")
                self.assertEqual(item["comparison"], "not_comparable")
                self.assertNotIn("sha256", item["base"])

    def test_parser_file_not_found_is_unreadable_unless_index_lookup_is_absent(self):
        base = ntfs()
        base.mft.root.children["folder"].children["same.txt"] = FileNotFoundError("missing index stream")
        self.assertEqual(compare(base, ntfs(Record()))["paths"][0]["base"]["status"], "unreadable")

    def test_stale_directory_index_sequence_is_not_current_or_deleted_content(self):
        record = Record()
        record.index_sequence = record.header.SequenceNumber - 1
        item = compare(ntfs(record), ntfs(Record()))["paths"][0]
        self.assertEqual(item["base"]["status"], "unsupported")
        self.assertIn("sequence", item["base"]["detail"])
        self.assertEqual(record.opened, 0)

    def test_cross_volume_serial_and_path_are_rejected(self):
        item = compare(ntfs(Record(), serial=SERIAL + 1), ntfs(Record()))["paths"][0]
        self.assertEqual(item["base"]["status"], "unsupported")
        for path in (r"D:\folder\same.txt", r"C:folder\same.txt", r"C:\..\same.txt", r"C:\*.txt",
                     r"C:\same.txt:secret", r"\\server\folder\same.txt", "C:/folder/same.txt"):
            with self.subTest(path=path), self.assertRaises((ValueError, h.SourceSelectionError)):
                h.compare_versions(inventory(), COPY, [path])

    def test_same_fs_multiple_drive_mappings_is_not_guessed(self):
        fs = filesystem()
        with patch.object(h, "_parse_vss", return_value=parsed([store()])):
            inv = h.discover_vss(NS(filesystems=[fs], fs=NS(mounts={"c:": fs, "d:": fs})), COMMON)
        with self.assertRaises(h.SourceSelectionError):
            h.compare_versions(inv, COPY, [PATH])

    def test_file_and_total_content_limits_apply_to_both_sides(self):
        for limits, expected in ((h.Limits(max_file_bytes=2), ("limit_exceeded", "limit_exceeded")),
                                 (h.Limits(max_total_bytes=5), ("present", "limit_exceeded"))):
            before, after = Record(b"abcd"), Record(b"abcd")
            report = compare(ntfs(before), ntfs(after), inv=inventory(limits=limits))
            item = report["paths"][0]
            self.assertEqual((item["base"]["status"], item["snapshot"]["status"]), expected)
            self.assertLessEqual(report["usage"]["content_bytes"], limits.max_total_bytes)
            self.assertEqual(after.opened, 0)

    def test_truncated_content_never_gets_a_complete_hash(self):
        item = compare(ntfs(Record(b"abc", declared_size=5)), ntfs(Record()))["paths"][0]
        self.assertEqual(item["base"]["status"], "unreadable")
        self.assertNotIn("sha256", item["base"])

    def test_parser_io_limit_is_reported_on_each_source_without_false_absence(self):
        inv = inventory(limits=h.Limits(max_io_bytes=8))
        with patch.object(h, "_open_ntfs", side_effect=lambda stream: stream.read(16)):
            item = h.compare_versions(inv, COPY, [PATH])["paths"][0]
        self.assertEqual(item["base"]["status"], "limit_exceeded")
        self.assertEqual(item["snapshot"]["status"], "limit_exceeded")
        self.assertEqual(item["comparison"], "not_comparable")

    def test_snapshot_open_failure_keeps_base_observation(self):
        inv = inventory()
        inv.sources[0].store.open.side_effect = OSError("missing snapshot blocks")
        with patch.object(h, "_open_ntfs", return_value=ntfs(Record())):
            item = h.compare_versions(inv, COPY, [PATH])["paths"][0]
        self.assertEqual(item["base"]["status"], "present")
        self.assertEqual(item["snapshot"]["status"], "unreadable")
        self.assertEqual(item["snapshot"]["provenance"]["source_snapshot"], "vss:" + str(COPY))

    def test_snapshot_storage_on_another_volume_is_not_implicitly_bound(self):
        fs = filesystem()
        source = store()
        parser = parsed([source])
        parser.store_volume_identifier = UUID(int=99)
        with patch.object(h, "_parse_vss", return_value=parser):
            inv = h.discover_vss(NS(filesystems=[fs], fs=NS(mounts={"c:": fs})), COMMON)
        with patch.object(h, "_open_ntfs", return_value=ntfs(Record())):
            item = h.compare_versions(inv, COPY, [PATH])["paths"][0]
        self.assertEqual(item["base"]["status"], "present")
        self.assertEqual(item["snapshot"]["status"], "unsupported")
        source.open.assert_not_called()

    def test_path_list_and_limits_validation(self):
        for paths in ([], PATH, [PATH, PATH.lower()], [PATH, r"C:\other.txt"]):
            with self.subTest(paths=paths), self.assertRaises(ValueError):
                h.compare_versions(inventory(limits=h.Limits(max_files=1)), COPY, paths)
        for value in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                h.Limits(max_files=value)


class ResourceBoundTests(unittest.TestCase):
    def test_underlying_read_and_call_limits_precede_reads(self):
        raw = io.BytesIO(b"0123456789")
        limited = h._BoundedStream(raw, h._Budget(5, 2))
        self.assertEqual(limited.read(3), b"012")
        with self.assertRaises(h.LimitExceeded):
            limited.read(3)
        self.assertEqual(raw.tell(), 3)
        self.assertEqual(limited.read(2), b"34")
        with self.assertRaises(h.LimitExceeded):
            limited.read(0)
        with self.assertRaises(h.LimitExceeded):
            h._BoundedStream(raw, h._Budget(100, 10)).read()
        limited.close()
        self.assertFalse(raw.closed)

    def _catalog(self, kinds=(1,), *, cycle=False, hidden=False):
        try:
            from dissect.volume import vss
        except ImportError:
            self.skipTest("Dissect extraction dependency is not installed")
        image = bytearray(3 * vss.BLOCK_SIZE)
        header = vss.c_vss.volume_header(identifier=vss.VSS_IDENTIFIER, catalog_offset=vss.BLOCK_SIZE)
        image[vss.VOLUME_HEADER_OFFSET:vss.VOLUME_HEADER_OFFSET + len(header)] = header.dumps()
        block = vss.c_vss.catalog_header(identifier=vss.VSS_IDENTIFIER,
            next_offset=vss.BLOCK_SIZE if cycle else 2 * vss.BLOCK_SIZE)
        image[vss.BLOCK_SIZE:vss.BLOCK_SIZE + len(block)] = block.dumps()
        for index, kind in enumerate(kinds):
            struct.pack_into("<Q", image, vss.BLOCK_SIZE + 128 + index * 128, kind)
        tail = vss.c_vss.catalog_header(identifier=vss.VSS_IDENTIFIER, next_offset=0)
        image[2 * vss.BLOCK_SIZE:2 * vss.BLOCK_SIZE + len(tail)] = tail.dumps()
        if hidden:
            struct.pack_into("<Q", image, 2 * vss.BLOCK_SIZE + 128, 1)
        return h._BoundedStream(io.BytesIO(image), h._Budget(len(image) * 8, 100))

    def test_raw_catalog_cycle_and_hidden_entries_are_refused(self):
        for kwargs in ({"cycle": True}, {"hidden": True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(h.UnsupportedSource):
                h._parse_vss(self._catalog(**kwargs), h.Limits())

    def test_raw_catalog_entry_limit_and_normal_padding(self):
        with self.assertRaises(h.LimitExceeded):
            h._parse_vss(self._catalog(kinds=(1, 1)), h.Limits(max_catalog_entries=1))
        parsed_catalog = h._parse_vss(self._catalog(), h.Limits())
        self.assertEqual(parsed_catalog.catalog.stores, [])


class OpticalDescriptorTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "disc.img"
        data, _ = make_disc()
        path.write_bytes(data)
        self.survey = optical.survey(path)
        self.addCleanup(self.survey.close)
        self.common = dict(COMMON, image="disc.img", source_snapshot="optical-image")

    def test_explicit_vat_disambiguates_same_file_set_descriptor(self):
        inv = h.discover_optical(self.survey, self.common)
        self.assertTrue(inv.complete, inv.issues)
        self.assertEqual([s.metadata["descriptor_id"] for s in inv.sources],
                         ["udf:vat=293:fsd=288", "udf:vat=303:fsd=288"])
        older = h.select_optical(inv, "udf:vat=293:fsd=288")
        newer = h.select_optical(inv, "udf:vat=303:fsd=288")
        self.assertIn(r"\a.txt", [f.path for f in older.version.files])
        self.assertIn(r"\a.txt", newer.version.nameless)
        self.assertEqual(newer.metadata["nameless_deleted_entries"], 1)
        self.assertEqual(older.metadata["provenance"]["source_snapshot"], "optical-image")
        self.assertNotEqual(older.metadata["provenance"]["source_variant"], newer.metadata["provenance"]["source_variant"])
        self.assertEqual(older.metadata["fsd_sha256"], newer.metadata["fsd_sha256"])
        json.dumps(inv.as_dict())

    def test_optical_does_not_guess_session_latest_or_time(self):
        inv = h.discover_optical(self.survey, self.common)
        for identity in (None, "latest", "session:2", "2015-03-24", "udf:vat=999:fsd=288", "udf:fsd=288"):
            with self.subTest(identity=identity), self.assertRaises(h.SourceSelectionError):
                h.select_optical(inv, identity)
        gap = h.optical_session_capability()
        self.assertEqual(gap["status"], "unsupported")
        self.assertIn("extractor.optical.Udf._versions", gap["audited_source"])

    def test_optical_partial_or_mixed_sources_do_not_support_selection(self):
        self.survey.udf.versions[0].files[0].version = 1
        inv = h.discover_optical(self.survey, self.common)
        self.assertFalse(inv.complete)
        with self.assertRaises(h.SourceSelectionError):
            h.select_optical(inv, "udf:vat=293:fsd=288")

    def test_optical_source_and_entry_limits_are_explicit(self):
        for limits in (h.Limits(max_sources=1), h.Limits(max_optical_entries=1), h.Limits(max_metadata_bytes=10)):
            inv = h.discover_optical(self.survey, self.common, limits=limits)
            self.assertFalse(inv.complete)
            self.assertEqual(inv.issues[-1]["status"], "limit_exceeded")

    def test_optical_parser_errors_do_not_become_absence(self):
        self.survey.udf.problems.append(("directory sector 289", OSError("short read")))
        inv = h.discover_optical(self.survey, self.common)
        self.assertFalse(inv.complete)
        self.assertEqual(inv.issues[0]["status"], "unreadable")
        with self.assertRaises(h.SourceSelectionError):
            h.select_optical(inv, "udf:vat=293:fsd=288")


if __name__ == "__main__":
    unittest.main()
