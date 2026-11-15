"""Inferring a name from a later OLD_NAME record needs intact bytes, identity and a bounded rename pair."""
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
from tests.test_journal_events import BASE_FT, COMMON, Collector, Mft, ROOT, record
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

    def test_missing_prefix_diagnostic_identifies_the_exact_unresolved_ancestor(self):
        ranges, entries, *_ = fixture([
            ('child.txt', CHILD, PARENT, ft.USN_FILE_CREATE, 0x20),
            ('Stage', PARENT, (99, 4), ft.USN_RENAME_OLD, 0x10),
            ('Renamed', PARENT, (99, 4), ft.USN_RENAME_NEW, 0x10)])
        resolved = ranges.resolve_folder(PARENT, entries[0].usn, ROOT)
        self.assertEqual(resolved['components'], ['Stage'])
        self.assertFalse(resolved['path_complete'])
        diagnostic = resolved['diagnostic']
        self.assertEqual(diagnostic['reason'], 'no_directory_observation')
        self.assertEqual(diagnostic['missing_ancestor'], {'file_record': 99, 'file_sequence': 4})
        self.assertEqual(diagnostic['resolved_chain_child_to_root'], [
            {'file_record': 10, 'file_sequence': 3, 'anchor_usn': entries[1].usn}])
        self.assertEqual(diagnostic['directory_observations_for_identity'], 0)
        self.assertEqual(diagnostic['child_intact_interval'], ranges.span(entries[0].usn))
        self.assertIn('exact record-and-sequence', diagnostic['evidence_needed'])
        self.assertIn('not a recovered prefix', diagnostic['limitation'])

    def test_child_between_rename_endpoints_has_no_supported_directory_name(self):
        ranges, entries, *_ = fixture([
            ('Before', PARENT, ROOT, ft.USN_RENAME_OLD, 0x10),
            ('during.txt', CHILD, PARENT, ft.USN_FILE_CREATE, 0x20),
            ('After', PARENT, ROOT, ft.USN_RENAME_NEW, 0x10),
            ('later.txt', (41, 1), PARENT, ft.USN_FILE_CREATE, 0x20)])
        during = ranges.resolve_folder(PARENT, entries[1].usn, ROOT)
        self.assertFalse(during['path_complete'])
        self.assertEqual(during['components'], [])
        self.assertEqual(during['diagnostic']['reason'], 'rename_transition_in_progress')
        after = ranges.resolve_folder(PARENT, entries[3].usn, ROOT)
        self.assertEqual(after['components'], ['After'])
        self.assertTrue(after['path_complete'])
        self.assertIsNone(after['diagnostic'])

    def test_reused_record_number_is_diagnostic_only_never_an_ancestry_join(self):
        ranges, entries, *_ = fixture([
            ('replacement', (10, 4), ROOT, ft.USN_FILE_CREATE, 0x10),
            ('child.txt', CHILD, PARENT, ft.USN_FILE_CREATE, 0x20)])
        resolved = ranges.resolve_folder(PARENT, entries[1].usn, ROOT)
        self.assertFalse(resolved['path_complete'])
        self.assertEqual(resolved['components'], [])
        self.assertEqual(resolved['diagnostic']['reason'], 'different_reference_sequence_only')
        self.assertEqual(resolved['diagnostic']['other_observed_sequences'], [4])

    def test_future_ordinary_name_and_non_directory_identity_are_not_anchors(self):
        child = ('child.txt', CHILD, PARENT, ft.USN_FILE_CREATE, 0x20)
        for entries, reason in (
            ([child, ('Future', PARENT, ROOT, 2, 0x10)], 'future_name_without_bounded_old_new_pair'),
            ([('not-a-directory', PARENT, ROOT, 2, 0x20), child], 'identity_not_exclusively_directory')):
            with self.subTest(reason=reason):
                ranges, parsed, *_ = fixture(entries)
                child_usn = next(e.usn for e in parsed if e.own == CHILD)
                result = ranges.resolve_folder(PARENT, child_usn, ROOT)
                self.assertFalse(result['path_complete'])
                self.assertEqual(result['diagnostic']['reason'], reason)

    def test_cycles_root_mismatch_and_unvalidated_child_cannot_complete(self):
        ranges, entries, *_ = fixture([
            ('A', PARENT, (11, 7), 2, 0x10),
            ('B', (11, 7), PARENT, 2, 0x10),
            ('child.txt', CHILD, PARENT, ft.USN_FILE_CREATE, 0x20)])
        cycle = ranges.resolve_folder(PARENT, entries[2].usn, ROOT)
        self.assertFalse(cycle['path_complete'])
        self.assertEqual(cycle['diagnostic']['reason'], 'ancestor_cycle')
        self.assertEqual(len(cycle['diagnostic']['resolved_chain_child_to_root']), 2)
        for ref, usn, root, reason in (
            ((5, 99), entries[2].usn, ROOT, 'root_reference_sequence_mismatch'),
            (ROOT, entries[2].usn, None, 'root_identity_unavailable'),
            (ROOT, 999_999, ROOT, 'child_record_outside_validated_interval')):
            with self.subTest(reason=reason):
                result = ranges.resolve_folder(ref, usn, root)
                self.assertFalse(result['path_complete'])
                self.assertEqual(result['diagnostic']['reason'], reason)

    def test_missing_bytes_report_the_interval_boundary(self):
        ranges, entries, *_ = fixture(gap=b'damaged!')
        result = ranges.resolve_folder(PARENT, entries[0].usn, ROOT)
        self.assertFalse(result['path_complete'])
        self.assertEqual(result['diagnostic']['reason'], 'directory_observation_outside_intact_interval')
        self.assertEqual(result['diagnostic']['child_intact_interval']['record_count'], 1)

    def test_preceding_multi_directory_chain_still_completes(self):
        ranges, entries, *_ = fixture([
            ('Top', (99, 4), ROOT, 2, 0x10),
            ('Nested', PARENT, (99, 4), 2, 0x10),
            ('child.txt', CHILD, PARENT, ft.USN_FILE_CREATE, 0x20)])
        result = ranges.resolve_folder(PARENT, entries[2].usn, ROOT)
        self.assertEqual(result['components'], ['Top', 'Nested'])
        self.assertTrue(result['path_complete'])
        self.assertIsNone(result['diagnostic'])

    def test_extractor_keeps_missing_prefix_scoped_and_present_mft_context_separate(self):
        _ranges, _entries, stream, records = fixture([
            ('child.txt', CHILD, PARENT, ft.USN_FILE_CREATE, 0x20),
            ('Stage', PARENT, (99, 4), ft.USN_RENAME_OLD, 0x10),
            ('Renamed', PARENT, (99, 4), ft.USN_RENAME_NEW, 0x10)])
        ntfs = NS(serial=0x12345678CA0C7A48, mft=Mft({10: (3, 'Present/Guess'), 99: (4, 'Guess')}),
                  usnjrnl=NS(fh=stream, records=lambda: iter(records)))
        ev = Collector()
        ft._journal(ev, ntfs, 'C:', '', COMMON, shadow_copy='snapshot-id')
        suffix = next(r for r in ev.rows if r['kind'] == 'journalPath')
        self.assertEqual(suffix['obj'], r'[unresolved ancestor]\Stage\child.txt')
        self.assertFalse(suffix['prov']['path_complete'])
        for kind in ('journalPath', 'journalName', 'journalParent', 'fileCreationRecorded'):
            row = next(r for r in ev.rows if r['kind'] == kind and r['prov']['raw_name'] == 'child.txt')
            diagnostic = row['prov']['path_resolution_diagnostic']
            self.assertEqual(diagnostic['missing_ancestor']['scoped_identity'],
                             ft._journal_identity(COMMON, ntfs.serial, (99, 4)))
            self.assertEqual(diagnostic['scope']['ntfs_volume_serial'], '12345678CA0C7A48')
            self.assertEqual(diagnostic['shadow_copy'], 'snapshot-id')
            self.assertTrue(diagnostic['scope_complete'])
            self.assertEqual(diagnostic['resolved_chain_child_to_root'][0]['scoped_identity'],
                             ft._journal_identity(COMMON, ntfs.serial, PARENT))
            self.assertNotIn('Guess', json.dumps(diagnostic))
        created = next(r for r in ev.rows if r['kind'] == 'fileCreationRecorded')
        self.assertEqual(created['obj'], 'child.txt')

    def test_no_suffix_retains_raw_observation_with_actionable_diagnostic(self):
        _ranges, _entries, stream, records = fixture([
            ('child.txt', CHILD, PARENT, ft.USN_FILE_CREATE, 0x20)])
        ntfs = NS(serial=0x12345678CA0C7A48, mft=Mft({10: (3, 'CurrentName')}),
                  usnjrnl=NS(fh=stream, records=lambda: iter(records)))
        ev = Collector()
        ft._journal(ev, ntfs, 'C:', '', COMMON)
        self.assertFalse(any(r['kind'] == 'journalPath' for r in ev.rows))
        name = next(r for r in ev.rows if r['kind'] == 'journalName')
        self.assertEqual(name['obj'], 'child.txt')
        self.assertFalse(name['prov']['historical_path_resolved'])
        self.assertEqual(name['prov']['path_resolution_diagnostic']['reason'], 'no_directory_observation')

    def test_unscoped_image_does_not_emit_bounded_or_direct_full_paths(self):
        for common in ({'image': 'pc.E01'}, {'exhibit': 'PC'}, {'image': ' ', 'exhibit': 'PC'}):
            with self.subTest(common=common):
                _ranges, _entries, stream, records = fixture()
                ntfs = NS(serial=0x12345678CA0C7A48, mft=Mft({10: (3, 'CurrentName')}),
                          usnjrnl=NS(fh=stream, records=lambda: iter(records)))
                ev = Collector()
                ft._journal(ev, ntfs, 'C:', '', common)
                self.assertFalse(any(r['kind'] == 'journalPath' for r in ev.rows))
                name = next(r for r in ev.rows if r['kind'] == 'journalName')
                self.assertEqual(name['obj'], 'child.txt')
                diagnostic = name['prov']['path_resolution_diagnostic']
                self.assertEqual(diagnostic['reason'], 'identity_scope_incomplete')
                self.assertIsNone(diagnostic['missing_ancestor']['scoped_identity'])
                self.assertFalse(diagnostic['scope_complete'])
                self.assertEqual(len(ev.problems), 1)

    def test_boolean_volume_serial_does_not_supply_a_valid_scope(self):
        for serial in (True, False):
            with self.subTest(serial=serial):
                _ranges, _entries, stream, records = fixture()
                ntfs = NS(serial=serial, mft=Mft({10: (3, 'CurrentName')}),
                          usnjrnl=NS(fh=stream, records=lambda: iter(records)))
                ev = Collector()
                ft._journal(ev, ntfs, 'C:', '', COMMON)
                self.assertFalse(any(r['kind'] == 'journalPath' for r in ev.rows))
                name = next(r for r in ev.rows if r['kind'] == 'journalName')
                self.assertEqual(name['obj'], 'child.txt')
                self.assertEqual(name['prov']['path_resolution_diagnostic']['reason'],
                                 'identity_scope_incomplete')

    def test_no_raw_bytes_never_resolve_paths_across_interleaved_rename(self):
        records = [
            record(1, 'Before', ft.USN_RENAME_OLD, own=PARENT, parent=ROOT),
            record(2, 'child.txt', ft.USN_FILE_CREATE | ft.USN_CLOSE, own=CHILD, parent=PARENT),
            record(3, 'After', ft.USN_RENAME_NEW | ft.USN_CLOSE, own=PARENT, parent=ROOT),
            record(4, 'child.txt', ft.USN_FILE_DELETE | ft.USN_CLOSE, own=CHILD, parent=PARENT)]
        ntfs = NS(serial=0x12345678CA0C7A48, mft=Mft({10: (3, 'After')}),
                  usnjrnl=NS(records=lambda: iter(records)))
        ev = Collector()
        ft._journal(ev, ntfs, 'C:', '', COMMON)
        self.assertFalse(any(r['kind'] == 'journalPath' for r in ev.rows))
        for kind in ('journalName', 'fileCreationRecorded', 'fileRemoved', 'journalRemoval'):
            rows = [r for r in ev.rows if r['kind'] == kind and r['prov']['file_record'] == CHILD[0]]
            self.assertTrue(rows)
            for row in rows:
                self.assertEqual(row['obj'], 'child.txt')
                self.assertFalse(row['prov'].get('historical_path_resolved', row['prov'].get('path_resolved')))
                self.assertEqual(row['prov']['path_resolution_diagnostic']['reason'],
                                 'raw_journal_coverage_unavailable')
        rename = next(r for r in ev.rows if r['kind'] == 'fileRenamed')
        self.assertEqual((rename['obj'], rename['aux']), ('Before', 'After'))
        self.assertFalse(rename['prov']['old_path_resolved'])
        self.assertFalse(rename['prov']['new_path_resolved'])
        for side in ('old', 'new'):
            self.assertEqual(rename['prov'][side + '_path_resolution_diagnostic']['reason'],
                             'raw_journal_coverage_unavailable')

    def test_old_direct_path_route_cannot_bypass_rename_or_gap_refusal(self):
        for entries, gap, child_index in (
            ([('Before', PARENT, ROOT, ft.USN_RENAME_OLD, 0x10),
              ('child.txt', CHILD, PARENT, ft.USN_FILE_CREATE, 0x20),
              ('After', PARENT, ROOT, ft.USN_RENAME_NEW, 0x10)], b'', 1),
            ([('Before', PARENT, ROOT, 2, 0x10),
              ('child.txt', CHILD, PARENT, ft.USN_FILE_CREATE, 0x20)], b'damaged!', 1)):
            with self.subTest(gap=gap):
                _ranges, parsed, stream, records = fixture(entries, gap)
                ntfs = NS(serial=0x12345678CA0C7A48, mft=Mft({10: (3, 'Present')}),
                          usnjrnl=NS(fh=stream, records=lambda: iter(records)))
                ev = Collector()
                ft._journal(ev, ntfs, 'C:', '', COMMON)
                for kind in ('journalName', 'fileCreationRecorded'):
                    row = next(r for r in ev.rows if r['kind'] == kind and r['prov']['usn'] == parsed[child_index].usn)
                    self.assertEqual(row['obj'], 'child.txt')
                    self.assertIsNotNone(row['prov']['path_resolution_diagnostic'])

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
