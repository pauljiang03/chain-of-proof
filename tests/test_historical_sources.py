"""Exact historical identity and byte-origin controls using parser fixtures."""
import copy
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from functools import lru_cache
import hashlib
import io
import json
import struct
import subprocess
import sys
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
        entries = []
        for name in sorted(self.children, key=str.upper):
            entry = self.search(name)
            entries.append(index_entry(name, record_entry=entry))
        entries.append(index_entry())
        return NS(root=NS(collation_rule=1, entries=lambda: iter(entries)),
                  index_buffer=Mock(side_effect=AssertionError("leaf has no child nodes")))

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


def index_entry(name=None, *, child=None, record_entry=None):
    data = bytearray(66)
    if name is not None:
        encoded = name.encode("utf-16-le")
        data[64] = len(encoded) // 2
        data.extend(encoded)
    entry = NS(buf=bytes(data), key_length=len(data), is_end=name is None,
               is_node=child is not None, node_vcn=child)
    if record_entry is not None:
        entry.dereference = record_entry.dereference
        entry.header = record_entry.header
    return entry


def directory_index(entries, children=None):
    children = children or {}
    root = NS(collation_rule=1, entries=lambda: iter(entries))
    return NS(root=root, index_buffer=Mock(side_effect=lambda vcn: children[vcn]))


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


class DirectoryIndexTests(unittest.TestCase):
    def test_real_dissect_cached_child_cycle_terminates_without_repeated_io(self):
        try:
            from dissect.ntfs.index import Index
            from dissect.ntfs.c_ntfs import COLLATION
        except ImportError:
            self.skipTest("Dissect extraction dependency is not installed")
        # This is the reviewer's native Index/cache reproduction. Native search
        # loops on this cached child; our lookup rejects the repeated VCN first.
        script = r'''
import json
from functools import lru_cache
from types import SimpleNamespace as NS
from unittest.mock import patch
from dissect.ntfs.index import Index
from dissect.ntfs.c_ntfs import COLLATION
from extractor import historical_sources as h
from tests.test_historical_sources import Record, index_entry
index = object.__new__(Index)
index.root = NS(collation_rule=COLLATION.FILE_NAME, entries=lambda: iter([index_entry(child=7)]))
index.index_buffer = lru_cache(128)(lambda _vcn: index.root)
record = Record(children={})
with patch.object(record, "index", return_value=index):
    try:
        h._record(NS(mft=NS(root=record)), r"C:\loop.txt")
    except h.UnsupportedSource as error:
        assert "cyclic" in str(error)
    else:
        raise AssertionError("cyclic directory index was not refused")
info = index.index_buffer.cache_info()
print(json.dumps(dict(misses=info.misses, hits=info.hits)))
'''
        done = subprocess.run([sys.executable, "-c", script], cwd=Path(__file__).resolve().parents[1],
                              capture_output=True, text=True, timeout=3)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(json.loads(done.stdout), {"misses": 1, "hits": 0})

    def test_multi_node_cycle_and_acyclic_depth_limit_are_distinct(self):
        one = NS(entries=lambda: iter([index_entry(child=9)]))
        two = NS(entries=lambda: iter([index_entry(child=7)]))
        index = directory_index([index_entry(child=7)], {7: one, 9: two})
        with self.assertRaisesRegex(h.UnsupportedSource, "cyclic"):
            h._index_search(index, "absent", h.Limits())
        self.assertEqual([call.args[0] for call in index.index_buffer.call_args_list], [7, 9])
        index = directory_index([index_entry(child=7)], {7: one, 9: two})
        with self.assertRaisesRegex(h.LimitExceeded, "node"):
            h._index_search(index, "absent", h.Limits(max_index_nodes=2))
        self.assertEqual([call.args[0] for call in index.index_buffer.call_args_list], [7])

    def test_entry_materialization_is_bounded_even_without_more_io(self):
        yielded = []

        def endless_entries():
            while True:
                yielded.append(1)
                yield index_entry("key")

        index = NS(root=NS(collation_rule=1, entries=endless_entries))
        with self.assertRaisesRegex(h.LimitExceeded, "entry"):
            h._index_search(index, "key", h.Limits(max_index_entries=3))
        self.assertEqual(len(yielded), 4)  # One look-ahead detects the exceeded cap.

    def test_exact_and_child_routing_match_installed_primary_parser(self):
        try:
            from dissect.ntfs.index import Index
            from dissect.ntfs.c_ntfs import COLLATION
        except ImportError:
            self.skipTest("Dissect extraction dependency is not installed")
        for search in ("Alpha", "ALPHA", "lambda", "MIDDLE", "OMEGA", "zzz", "not-present"):
            with self.subTest(search=search):
                leaf = NS(entries=lambda: iter([index_entry("alpha"), index_entry("lambda"), index_entry()]))
                high = NS(entries=lambda: iter([index_entry("omega"), index_entry()]))
                entries = [index_entry("middle", child=7), index_entry(child=9)]
                expected = object.__new__(Index)
                expected.root = NS(collation_rule=COLLATION.FILE_NAME, entries=lambda: iter(entries))
                expected.index_buffer = lru_cache(128)(lambda vcn: {7: leaf, 9: high}[vcn])
                try:
                    actual = expected.search(search)
                except KeyError:
                    with self.assertRaises(h._PathAbsent):
                        h._index_search(expected, search, h.Limits())
                else:
                    self.assertEqual(h._index_search(expected, search, h.Limits()).buf, actual.buf)

    def test_malformed_or_unsupported_nodes_never_become_absence(self):
        for index in (directory_index([]), directory_index([index_entry("no-end")]),
                      directory_index([index_entry(), index_entry()])):
            with self.assertRaises(h.UnsupportedSource):
                h._index_search(index, "x", h.Limits())
        index = directory_index([index_entry()])
        index.root.collation_rule = 16
        with self.assertRaisesRegex(h.UnsupportedSource, "collation"):
            h._index_search(index, "x", h.Limits())
        index = directory_index([index_entry(child=7)])
        index.index_buffer.side_effect = KeyError("malformed parser child lookup")
        base = ntfs()
        with patch.object(base.mft.root, "index", return_value=index):
            item = compare(base, ntfs(Record()))["paths"][0]
        self.assertEqual(item["base"]["status"], "unreadable")

    def test_unsorted_names_cannot_turn_a_present_key_into_absence(self):
        unsorted = [index_entry("b"), index_entry("a"), index_entry()]
        for index in (directory_index(unsorted), directory_index([index_entry(child=7)],
                      {7: NS(entries=lambda: iter(unsorted))})):
            with self.assertRaisesRegex(h.UnsupportedSource, "not sorted"):
                h._index_search(index, "b", h.Limits())
        entries = [index_entry("a"), index_entry("B"), index_entry()]
        self.assertEqual(h._index_search(directory_index(entries), "b", h.Limits()).buf, entries[1].buf)

    def test_cycle_and_node_cap_statuses_survive_comparison_reporting(self):
        for cap, expected in ((128, "unsupported"), (1, "limit_exceeded")):
            base = ntfs()
            index = directory_index([index_entry(child=7)])
            index.index_buffer.side_effect = lambda _vcn: index.root
            with patch.object(base.mft.root, "index", return_value=index):
                item = compare(base, ntfs(Record()), inv=inventory(limits=h.Limits(max_index_nodes=cap)))["paths"][0]
            self.assertEqual(item["base"]["status"], expected)
            self.assertEqual(item["snapshot"]["status"], "present")
            self.assertEqual(item["comparison"], "not_comparable")
            self.assertNotIn("sha256", item["base"])


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

    def test_optical_whole_image_variant_cannot_be_silently_replaced(self):
        primary = h.discover_optical(self.survey, self.common)
        self.assertTrue(primary.complete)
        for variant in ("alternate", "recovered", "udf:vat=293:fsd=288", "unknown"):
            with self.subTest(variant=variant), self.assertRaises(ValueError):
                h.discover_optical(self.survey, dict(self.common, source_variant=variant))

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


class CLITests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.image = self.root / "input.img"
        self.image.write_bytes(b"synthetic source image")
        self.output = self.root / "observation.json"
        fs = filesystem()
        self.target = NS(filesystems=[fs], fs=NS(mounts={"c:": fs}))

    def invoke(self, command="discover", extra=(), *, open_effect=None):
        args = [command, "--image", str(self.image), "--exhibit", "PC", "--out", str(self.output), *extra]
        with ExitStack() as stack:
            stack.enter_context(redirect_stdout(io.StringIO()))
            stack.enter_context(redirect_stderr(io.StringIO()))
            opened = stack.enter_context(patch.object(h, "_target_open", side_effect=open_effect,
                                                       return_value=self.target))
            stack.enter_context(patch.object(h, "_parse_vss", return_value=parsed([store()])))
            stack.enter_context(patch.object(h, "_open_ntfs", side_effect=[ntfs(Record(b"base")), ntfs(Record(b"past"))]))
            try:
                status = h.main(args)
            except SystemExit as error:
                status = error.code
        return status, opened

    def config(self, *, exhibit="PC", size=None):
        from extractor.intake import _digest
        value = dict(schema_version=1, images_root=str(self.image.resolve().parent), snapshot_id="public-intake-fixture",
            manifest={self.image.name: dict(exhibit=exhibit, role="pc")},
            images=[dict(image=self.image.name, exhibit=exhibit,
                segments=[dict(name=self.image.name, bytes=self.image.stat().st_size if size is None else size, sha256="0" * 64)])])
        value["config_sha256"] = _digest(value)
        path = self.root / "intake-config.json"
        path.write_text(json.dumps(value))
        return path

    def test_discover_receipt_binds_code_and_stats_without_claiming_image_hash(self):
        before = self.image.read_bytes()
        status, _ = self.invoke()
        self.assertEqual(status, 0)
        report = json.loads(self.output.read_text())
        self.assertEqual(report["command"], "discover")
        self.assertIn("Observation-only", report["interpretation"])
        self.assertEqual(report["code"]["sha256"], hashlib.sha256(Path(h.__file__).read_bytes()).hexdigest())
        self.assertEqual(report["code"]["hash_status"], "recomputed")
        self.assertEqual(report["input"]["segments"][0]["content_hash_status"], "not_recomputed")
        self.assertIsNone(report["input"]["segments"][0]["content_sha256"])
        self.assertEqual(report["result"]["sources"][0]["copy_uuid"], str(COPY))
        self.assertEqual(self.image.read_bytes(), before)

    def test_compare_requires_explicit_id_and_paths_before_opening_image(self):
        for extra in ([], ["--copy-uuid", "latest", "--path", PATH], ["--copy-uuid", str(COPY)],
                      ["--copy-uuid", str(COPY), "--path", r"C:relative.txt"]):
            with self.subTest(extra=extra):
                status, opened = self.invoke("compare", extra)
                self.assertEqual(status, 2)
                opened.assert_not_called()
                self.assertFalse(self.output.exists())

    def test_compare_receipt_keeps_both_origins_and_explicit_requested_id(self):
        status, _ = self.invoke("compare", ["--copy-uuid", "{" + str(COPY).upper() + "}", "--path", PATH])
        self.assertEqual(status, 0)
        report = json.loads(self.output.read_text())
        self.assertEqual(report["request"]["copy_uuid"], str(COPY))
        row = report["result"]["paths"][0]
        self.assertEqual(row["comparison"], "different_content")
        self.assertEqual(row["base"]["provenance"]["source_snapshot"], "base-volume")
        self.assertEqual(row["snapshot"]["provenance"]["source_snapshot"], "vss:" + str(COPY))

    def test_unknown_id_does_not_publish_a_guessed_source(self):
        status, _ = self.invoke("compare", ["--copy-uuid", str(UUID(int=999)), "--path", PATH])
        self.assertEqual(status, 2)
        self.assertFalse(self.output.exists())

    def test_existing_output_and_creation_race_never_overwrite(self):
        self.output.write_text("keep existing")
        status, opened = self.invoke()
        self.assertEqual(status, 2)
        opened.assert_not_called()
        self.assertEqual(self.output.read_text(), "keep existing")
        self.output.unlink()

        def race(_path):
            self.output.write_text("created concurrently")
            return self.target

        status, _ = self.invoke(open_effect=race)
        self.assertEqual(status, 2)
        self.assertEqual(self.output.read_text(), "created concurrently")

    def test_declared_intake_hash_is_never_called_recomputed(self):
        config = self.config()
        status, _ = self.invoke(extra=["--intake-config", str(config)])
        self.assertEqual(status, 0)
        report = json.loads(self.output.read_text())
        declared = report["input"]["segments"][0]
        self.assertEqual(declared["content_sha256"], "0" * 64)
        self.assertEqual(declared["content_hash_status"], "declared_by_intake_not_recomputed")
        config_receipt = report["input"]["intake_config"]
        self.assertEqual(config_receipt["file_sha256"], hashlib.sha256(config.read_bytes()).hexdigest())
        self.assertEqual(config_receipt["file_hash_status"], "recomputed")

    def test_config_digest_exhibit_and_size_mismatch_are_refused(self):
        for wrong in ("digest", "exhibit", "size"):
            config = self.config(exhibit="OTHER" if wrong == "exhibit" else "PC", size=99 if wrong == "size" else None)
            if wrong == "digest":
                value = json.loads(config.read_text())
                value["snapshot_id"] = "tampered"
                config.write_text(json.dumps(value))
            with self.subTest(wrong=wrong):
                status, opened = self.invoke(extra=["--intake-config", str(config)])
                self.assertEqual(status, 2)
                opened.assert_not_called()
                self.assertFalse(self.output.exists())

    def test_input_mutation_during_observation_prevents_publication(self):
        def mutate(_path):
            self.image.write_bytes(b"changed while open")
            return self.target

        status, _ = self.invoke(open_effect=mutate)
        self.assertEqual(status, 2)
        self.assertFalse(self.output.exists())

    def test_ewf_segment_names_sizes_are_recorded_without_full_hashing(self):
        self.image = self.root / "image.E01"
        self.image.write_bytes(optical.EWF_MAGIC[0] + b"first segment fixture")
        second = self.root / "image.E02"
        second.write_bytes(optical.EWF_MAGIC[0] + b"second segment fixture")
        status, _ = self.invoke()
        self.assertEqual(status, 0)
        parts = json.loads(self.output.read_text())["input"]["segments"]
        self.assertEqual([(part["name"], part["bytes"]) for part in parts],
                         [(self.image.name, self.image.stat().st_size), (second.name, second.stat().st_size)])
        self.assertTrue(all(part["content_hash_status"] == "not_recomputed" for part in parts))

    def test_input_and_output_symlinks_are_refused(self):
        self.output.symlink_to(self.root / "nonexistent-target.json")
        status, opened = self.invoke()
        self.assertEqual(status, 2)
        opened.assert_not_called()
        self.assertFalse(self.output.resolve().exists())
        self.output.unlink()
        linked = self.root / "linked.img"
        linked.symlink_to(self.image)
        self.image = linked
        status, opened = self.invoke()
        self.assertEqual(status, 2)
        opened.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_incomplete_observation_is_written_with_nonzero_status(self):
        status, _ = self.invoke("compare", ["--copy-uuid", str(COPY), "--path", PATH, "--max-file-bytes", "1"])
        self.assertEqual(status, 1)
        report = json.loads(self.output.read_text())
        self.assertEqual(report["result"]["paths"][0]["base"]["status"], "limit_exceeded")
        self.assertEqual(report["result"]["paths"][0]["comparison"], "not_comparable")


if __name__ == "__main__":
    unittest.main()
