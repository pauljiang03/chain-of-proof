"""Future OLD_NAME inference requires intact bytes, identity and a bounded rename pair."""
import io
import json
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace as NS
import unittest

from checker.check import check
from checker.facts import JsonFacts
from extractor import filetraces as ft
from extractor.journal_paths import JournalRanges, parse_record
from extractor.store import Evidence
from tests.test_journal_events import BASE_FT, COMMON, Mft, ROOT, record
from verifier.verify import verify

CHILD, PARENT = (40, 2), (10, 3)


def encode(offset, name, own, parent, reason, attrs):
    text = name.encode('utf-16-le')
    size = (60 + len(text) + 7) // 8 * 8
    packed = lambda ref: ref[0] | ref[1] << 48
    raw = struct.pack('<IHHQQqQIIIIHH', size, 2, 0, packed(own), packed(parent), offset,
                      BASE_FT + offset * 10_000_000, reason, 0, 0, attrs, len(text), 60) + text
    return raw.ljust(size, b'\0')


def fixture(entries=None, gap=b''):
    entries = entries or [('child.txt', CHILD, PARENT, ft.USN_FILE_CREATE | ft.USN_CLOSE, 0x20),
                          ('Stage', PARENT, ROOT, ft.USN_RENAME_OLD, 0x10),
                          ('Renamed', PARENT, ROOT, ft.USN_RENAME_NEW | ft.USN_CLOSE, 0x10)]
    image, parsed, records = bytearray(), [], []
    for n, (name, own, parent, reason, attrs) in enumerate(entries):
        if n == 1:
            image += gap
        offset = len(image)
        raw = encode(offset, name, own, parent, reason, attrs)
        image += raw
        parsed.append(parse_record(raw, offset))
        r = record(offset, name, reason, own=own, parent=parent)
        r.offset = offset
        r.record.RecordLength = len(raw)
        records.append(r)
    stream, ranges = io.BytesIO(image), JournalRanges()
    for entry in parsed:
        ranges.capture(entry.usn, entry.length, stream)
    ranges.finish()
    return ranges, parsed, stream, records


class BoundedJournalPaths(unittest.TestCase):
    def test_future_old_name_resolves_only_with_intact_interval_and_matching_new_name(self):
        ranges, entries, _stream, _records = fixture()
        folders, complete, anchors = ranges.folder(PARENT, entries[0].usn, ROOT)
        self.assertEqual((folders, complete), (['Stage'], True))
        self.assertEqual(anchors[0]['anchor_usn'], entries[1].usn)
        self.assertTrue(anchors[0]['method'].startswith('future OLD_NAME'))
        self.assertEqual(anchors[0]['intact_range']['record_count'], 3)
        self.assertEqual(len(anchors[0]['intact_range']['sha256']), 64)

    def test_nonzero_gaps_and_missing_whole_pages_block_backdating(self):
        for gap in (b'damaged!', bytes(8192)):
            with self.subTest(gap_length=len(gap)):
                ranges, entries, *_ = fixture(gap=gap)
                self.assertFalse(ranges.same_block(entries[0].usn, entries[1].usn))
                self.assertIsNone(ranges.folder(PARENT, entries[0].usn, ROOT))

    def test_only_zero_tail_padding_to_next_page_is_allowed(self):
        child_size = len(encode(0, 'child.txt', CHILD, PARENT, ft.USN_FILE_CREATE | ft.USN_CLOSE, 0x20))
        ranges, entries, *_ = fixture(gap=bytes(4096 - child_size))
        self.assertTrue(ranges.same_block(entries[0].usn, entries[1].usn))
        self.assertEqual(ranges.folder(PARENT, entries[0].usn, ROOT)[0], ['Stage'])

    def test_new_name_without_old_create_flag_conflicts_and_reused_reference_are_refused(self):
        child = ('child.txt', CHILD, PARENT, ft.USN_FILE_CREATE | ft.USN_CLOSE, 0x20)
        old = ('Stage', PARENT, ROOT, ft.USN_RENAME_OLD, 0x10)
        new = ('Renamed', PARENT, ROOT, ft.USN_RENAME_NEW | ft.USN_CLOSE, 0x10)
        cases = [[child, new], [child, old],
                 [child, ('other', PARENT, ROOT, 2, 0x10), old, new],
                 [child, ('Stage', PARENT, ROOT, ft.USN_FILE_CREATE, 0x10), old, new],
                 [child, old, ('Renamed', PARENT, ROOT, ft.USN_RENAME_NEW | ft.USN_FILE_DELETE, 0x10)],
                 [child, ('Stage', (10, 4), ROOT, ft.USN_RENAME_OLD, 0x10),
                         ('Renamed', (10, 4), ROOT, ft.USN_RENAME_NEW, 0x10)]]
        for entries in cases:
            with self.subTest(entries=entries):
                ranges, parsed, *_ = fixture(entries)
                self.assertIsNone(ranges.folder(PARENT, parsed[0].usn, ROOT))

    def test_unknown_higher_parent_is_a_suffix_not_an_invented_absolute_path(self):
        ranges, entries, *_ = fixture([
            ('child.txt', CHILD, PARENT, ft.USN_FILE_CREATE, 0x20),
            ('Stage', PARENT, (99, 1), ft.USN_RENAME_OLD, 0x10),
            ('Renamed', PARENT, (99, 1), ft.USN_RENAME_NEW, 0x10)])
        folders, complete, _ = ranges.folder(PARENT, entries[0].usn, ROOT)
        self.assertEqual(folders, ['Stage'])
        self.assertFalse(complete)

    def test_unknown_version_and_wrong_usn_do_not_form_coverage(self):
        raw = bytearray(encode(0, 'child.txt', CHILD, PARENT, 0, 0x20))
        for mutate in (lambda b: struct.pack_into('<H', b, 4, 3),
                       lambda b: struct.pack_into('<q', b, 24, 8)):
            bad = bytearray(raw)
            mutate(bad)
            ranges = JournalRanges()
            self.assertIsNone(ranges.capture(0, len(bad), io.BytesIO(bad)))
            self.assertEqual(ranges.membership, {})
            self.assertEqual(ranges.rejected, 1)

    def test_extractor_adds_separate_path_observation_without_rewriting_creation(self):
        ranges, entries, stream, records = fixture()
        ntfs = NS(serial=0x12345678CA0C7A48, mft=Mft({10: (3, 'Renamed')}),
                  usnjrnl=NS(fh=stream, records=lambda: iter(records)))
        evidence = Evidence()
        ft._journal(evidence, ntfs, 'C:', '', COMMON)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'facts.json'
            evidence.write_json(path, {'case': 'Synthetic bounded path'})
            src = JsonFacts(path)
            rows = src.all()
            created = next(r for r in rows if r.kind == 'fileCreationRecorded')
            bounded = next(r for r in rows if r.kind == 'journalPath')
            self.assertEqual(src.string(created.obj), 'child.txt')
            self.assertEqual(src.string(bounded.obj), r'C:\Stage\child.txt')
            self.assertEqual(bounded.t, created.t)
            cert = check({'journalPathAt': [bounded.id]}, 'BoundedPath', src, out_dir=Path(directory))
            self.assertEqual(cert['status'], 'verified')
            self.assertEqual(verify(cert, src), [])
            self.assertIn('not creation onset', cert['english'])
            self.assertEqual(check({'fileCreatedAt': [bounded.id]}, 'NotCreation', src,
                                   out_dir=Path(directory))['status'], 'rejected')


if __name__ == '__main__':
    unittest.main()
