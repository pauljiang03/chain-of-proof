"""Identity joins preserve journal names, parent relations and observation times."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest

from checker import claims
from checker.check import check
from checker.facts import JsonFacts
from extractor import filetraces as ft
from extractor.store import Evidence
from miner import mine
from tests.test_journal_events import COMMON, ROOT, BASE_US, Collector, Mft, collect, record
from verifier.verify import verify


class JournalIdentityExtraction(unittest.TestCase):
    def test_parent_rename_changes_only_later_observed_paths_and_repeated_flags_are_compressed(self):
        from tests.test_journal_paths import fixture
        parent = (10, 3)
        _ranges, entries, stream, records = fixture([
            ('early', parent, ROOT, ft.USN_FILE_CREATE | ft.USN_CLOSE, 0x10),
            ('a.txt', (40, 2), parent, ft.USN_FILE_CREATE | ft.USN_CLOSE, 0x20),
            ('early', parent, ROOT, ft.USN_RENAME_OLD, 0x10),
            ('later', parent, ROOT, ft.USN_RENAME_NEW | ft.USN_CLOSE, 0x10),
            ('a.txt', (40, 2), parent, 2, 0x20),
            ('a.txt', (40, 2), parent, 2 | ft.USN_CLOSE, 0x20)])
        ntfs = NS(serial=0x12345678CA0C7A48, mft=Mft({10: (3, 'later')}),
                  usnjrnl=NS(fh=stream, records=lambda: iter(records)))
        ev = Collector()
        ft._journal(ev, ntfs, 'C:', '', COMMON)
        names = [r for r in ev.rows if r['kind'] == 'journalName' and r['prov']['file_record'] == 40]
        self.assertEqual([r['obj'] for r in names], [r'C:\early\a.txt', r'C:\later\a.txt'])
        self.assertEqual([r['t'] for r in names],
                         [BASE_US + entries[i].usn * 1_000_000 for i in (1, 4)])
        self.assertEqual([r['prov']['observation_count'] for r in names], [1, 2])
        self.assertEqual(names[1]['prov']['last_observation_usn'], entries[5].usn)
        parents = [r for r in ev.rows if r['kind'] == 'journalParent' and r['prov']['file_record'] == 40]
        self.assertEqual(len(parents), 1)
        self.assertEqual(parents[0]['prov']['observation_count'], 3)
        self.assertEqual(parents[0]['t'], BASE_US + entries[1].usn * 1_000_000)

    def test_later_name_and_current_mft_path_remain_context_not_earlier_historical_path(self):
        _, ev = collect([
            record(2, 'a.txt', ft.USN_FILE_CREATE | ft.USN_CLOSE),
            record(10, 'staging', ft.USN_RENAME_OLD, own=(10, 3), parent=ROOT),
            record(11, 'random', ft.USN_RENAME_NEW | ft.USN_CLOSE, own=(10, 3), parent=ROOT),
        ], identity=True, paths={10: (3, 'random')})
        early = next(r for r in ev.rows if r['kind'] == 'journalName' and r['prov']['file_record'] == 40)
        self.assertEqual(early['obj'], 'a.txt')
        self.assertFalse(early['prov']['historical_path_resolved'])
        self.assertEqual(early['prov']['context_path'], r'C:\random\a.txt')
        parent = next(r for r in ev.rows if r['kind'] == 'journalParent' and r['prov']['file_record'] == 40)
        later = next(r for r in ev.rows if r['kind'] == 'journalName' and r['obj'] == 'staging')
        self.assertFalse(later['prov']['historical_path_resolved'])
        self.assertEqual(later['prov']['path_resolution_diagnostic']['reason'],
                         'raw_journal_coverage_unavailable')
        self.assertEqual(parent['aux'], later['aux'])
        rename = next(r for r in ev.rows if r['kind'] == 'fileRenamed')
        self.assertEqual(rename['prov']['parent_sequence'], 1)
        self.assertEqual(rename['prov']['new_parent_sequence'], 1)
        self.assertEqual(rename['prov']['ntfs_volume_serial'], '12345678CA0C7A48')

    def test_identity_scopes_include_upper_volume_bits_image_and_sequence(self):
        own = (40, 2)
        identities = [ft._journal_identity(COMMON, 0x100000001, own),
                      ft._journal_identity(COMMON, 0x200000001, own),
                      ft._journal_identity(COMMON, 0x100000001, (40, 3)),
                      ft._journal_identity(dict(COMMON, image='other.E01'), 0x100000001, own)]
        self.assertEqual(len(set(identities)), 4)

    def test_creation_removal_and_both_rename_sides_do_not_inherit_current_or_future_parent_names(self):
        _, ev = collect([
            record(2, 'original.txt', ft.USN_FILE_CREATE | ft.USN_CLOSE),
            record(3, 'original.txt', ft.USN_RENAME_OLD),
            record(4, 'scrambled', ft.USN_RENAME_NEW | ft.USN_CLOSE),
            record(5, 'scrambled', ft.USN_FILE_DELETE | ft.USN_CLOSE),
            record(20, 'later-observed-old-parent', ft.USN_RENAME_OLD, own=(10, 3), parent=ROOT),
            record(21, 'current-parent', ft.USN_RENAME_NEW | ft.USN_CLOSE, own=(10, 3), parent=ROOT),
        ], identity=True, paths={10: (3, 'current-parent')})
        created = next(r for r in ev.rows if r['kind'] == 'fileCreationRecorded')
        removed = next(r for r in ev.rows if r['kind'] == 'fileRemoved')
        renamed = next(r for r in ev.rows if r['kind'] == 'fileRenamed'
                       and r['prov']['file_record'] == 40)
        self.assertEqual(created['obj'], 'original.txt')
        self.assertEqual(removed['obj'], 'scrambled')
        self.assertEqual((renamed['obj'], renamed['aux']), ('original.txt', 'scrambled'))
        for row in (created, removed, renamed):
            self.assertEqual(row['prov']['parent_folder'], 'not resolved')
            self.assertIn('current-parent', row['prov']['context_path'])
            self.assertIn('not asserted as', row['prov']['context_path_source'])
        self.assertFalse(renamed['prov']['old_path_resolved'])
        self.assertFalse(renamed['prov']['new_path_resolved'])
        self.assertEqual(renamed['prov']['new_context_path'], r'C:\current-parent\scrambled')


class JournalIdentityProofs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.directory = Path(cls.tmp.name)
        _, ev = collect([
            record(1, 'staging', ft.USN_FILE_CREATE | ft.USN_CLOSE, own=(10, 3), parent=ROOT),
            record(2, 'original.txt', ft.USN_FILE_CREATE | ft.USN_CLOSE),
            record(3, 'original.txt', ft.USN_RENAME_OLD),
            record(4, 'scrambled', ft.USN_RENAME_NEW | ft.USN_CLOSE),
            record(5, 'scrambled', ft.USN_FILE_DELETE | ft.USN_CLOSE),
            record(6, 'original.txt', ft.USN_FILE_CREATE | ft.USN_CLOSE, own=(40, 3)),
        ], identity=True, paths={10: (3, 'staging')})
        evidence = Evidence()
        for row in ev.rows:
            evidence.add(row['kind'], row['t'], row['res'], row['obj'], row['aux'], **row['prov'])
        identity = ft._journal_identity(COMMON, 0x12345678CA0C7A48, (40, 2))
        evidence.add('journalName', BASE_US + 9_000_000, 1, 'later-alias', identity,
                     test_fixture='later-name')
        evidence.add('journalName', BASE_US + 2_000_000, 1, 'original.txt',
                     ft._journal_identity(COMMON, 0x12345679CA0C7A48, (40, 2)),
                     test_fixture='different-volume')
        path = cls.directory / 'facts.json'
        evidence.write_json(path, {'case': 'Synthetic'})
        cls.source = JsonFacts(path)
        rows = cls.source.all()
        cls.old = next(f for f in rows if f.kind == 'journalName' and f.prov.get('file_record') == 40
                       and f.prov['file_sequence'] == 2 and f.prov['usn'] == 2)
        cls.new = next(f for f in rows if f.kind == 'journalName' and f.prov.get('usn') == 4)
        cls.removal = next(f for f in rows if f.kind == 'journalRemoval')
        cls.reused = next(f for f in rows if f.kind == 'journalName' and f.prov.get('file_sequence') == 3
                          and f.prov['file_record'] == 40)
        cls.parent = next(f for f in rows if f.kind == 'journalParent' and f.prov['file_record'] == 40
                          and f.prov['file_sequence'] == 2)
        cls.directory_name = next(f for f in rows if f.kind == 'journalName' and f.prov.get('file_record') == 10)
        cls.later_name = next(f for f in rows if f.prov.get('test_fixture') == 'later-name')
        cls.other_volume = next(f for f in rows if f.prov.get('test_fixture') == 'different-volume')
        cls.create_flag = next(f for f in rows if f.kind == 'fileCreationRecorded' and f.prov['usn'] == 2)
        cls.legacy_removal = next(f for f in rows if f.kind == 'fileRemoved')

    def test_name_removal_and_parent_links_certify_and_reverify(self):
        cases = [
            {'sameJournalFile': [self.old.id, self.new.id]},
            {'removedFilePreviouslyNamed': [self.old.id, self.removal.id]},
            {'journalChildNamedDirectory': [self.old.id, self.parent.id, self.directory_name.id]},
        ]
        for index, claim in enumerate(cases):
            with self.subTest(claim=claim):
                cert = check(claim, f'Identity{index}', self.source, out_dir=self.directory)
                self.assertEqual(cert['status'], 'verified')
                self.assertEqual(cert['axioms'], [])
                self.assertEqual(verify(cert, self.source), [])
        text = json.loads((self.directory / 'Identity1.json').read_text())['english']
        self.assertIn('does not place deletion at the earlier alias', text)
        self.assertIn('original.txt', text)
        self.assertIn('scrambled', text)

    def test_reuse_kind_mismatch_and_reversed_observations_are_refused(self):
        bad = [
            {'sameJournalFile': [self.old.id, self.reused.id]},
            {'sameJournalFile': [self.old.id, self.other_volume.id]},
            {'removedFilePreviouslyNamed': [self.later_name.id, self.removal.id]},
            {'removedFilePreviouslyNamed': [self.reused.id, self.removal.id]},
            {'removedFilePreviouslyNamed': [self.old.id, self.legacy_removal.id]},
            {'journalChildNamedDirectory': [self.reused.id, self.parent.id, self.directory_name.id]},
            {'journalChildNamedDirectory': [self.old.id, self.parent.id, self.reused.id]},
            {'fileCreatedAt': [self.old.id]}, {'copiedHere': [self.create_flag.id, self.old.id]},
            {'fileDeletedAt': [self.removal.id]},
        ]
        for claim in bad:
            with self.subTest(claim=claim):
                self.assertEqual(check(claim, 'BadIdentity', self.source,
                                       out_dir=self.directory)['status'], 'rejected')

    def test_miner_joins_exact_identity_without_promoting_the_old_name_to_creation(self):
        parts = [claims.to_json(p) for _q, c in mine.candidates(self.source)
                 for p in claims.parts(claims.parse(c))]
        self.assertIn({'sameJournalFile': [self.old.id, self.new.id]}, parts)
        self.assertIn({'removedFilePreviouslyNamed': [self.old.id, self.removal.id]}, parts)
        self.assertIn({'journalChildNamedDirectory': [self.old.id, self.parent.id, self.directory_name.id]}, parts)
        self.assertNotIn({'sameJournalFile': [self.old.id, self.reused.id]}, parts)
        self.assertFalse(any('fileCreatedAt' in p or 'copiedHere' in p for p in parts))


if __name__ == '__main__':
    unittest.main()
