"""The kernel distinguishes observations from actions and links optical times exactly."""
import json
from pathlib import Path
import tempfile
import unittest

from checker import claims
from checker.check import check
from checker.facts import Fact, FactSource, JsonFacts
from miner import mine
from verifier.verify import verify


class MemorySource(FactSource):
    def __init__(self, facts):
        self.facts = facts

    def all(self):
        return self.facts

    def get(self, ids):
        return {f.id: f for f in self.facts if f.id in ids}

    def string(self, sid):
        return str(sid)


class RecordedEvents(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.directory = Path(cls.tmp.name)
        spec = [
            (1, 'fileRemoved', 300, 1, 2),
            (2, 'fileDeleted', 310, 1, 2),
            (3, 'volumeRecorded', 100, 3, 2),
            (4, 'fileCreated', 200, 1, 2),
            (5, 'fileCreationRecorded', 205, 1, 2),
            (6, 'fileModified', 50, 1, 2),
            (7, 'fileCreated', 200, 1, 4),
            (8, 'fileCreated', 99, 1, 2),
            (9, 'volumeOnDevice', 100, 3, 2),
            (10, 'fileCreated', 102, 1, 2),
        ]
        path = cls.directory / 'facts.json'
        path.write_text(json.dumps({'strings': {'1': 'report.docx', '2': 'VOLUME1',
                                               '3': 'disc T7', '4': 'OTHER-VOLUME'},
                                   'facts': [dict(id=i, kind=k, t=t, res=1, obj=o, aux=a)
                                             for i, k, t, o, a in spec]}))
        cls.source = JsonFacts(path)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_observation_forms_certify_and_reverify_as_records_not_actions(self):
        for form, row in [('fileRemovedAt', 1), ('volumeRecordedAt', 3), ('fileCreationRecordedAt', 5)]:
            with self.subTest(form=form):
                cert = check({form: [row]}, form, self.source, out_dir=self.directory)
                self.assertEqual(cert['status'], 'verified')
                self.assertEqual(cert['axioms'], [])
                self.assertEqual(verify(cert, self.source), [])
                self.assertEqual([r['id'] for r in cert['cited_facts']], [row])
        removed = json.loads((self.directory / 'fileRemovedAt.json').read_text())['english']
        self.assertIn('not necessarily the deletion onset', removed)
        self.assertIn('does not establish Recycle Bin use, wiping', removed)
        created = json.loads((self.directory / 'fileCreationRecordedAt.json').read_text())['english']
        self.assertIn('not a filesystem creation timestamp', created)

    def test_journal_flags_cannot_certify_recycling_filesystem_creation_or_copy_signature(self):
        for claim in ({'fileDeletedAt': [1]}, {'fileCreatedAt': [5]}, {'copiedHere': [5, 6]},
                      {'fileRemovedAt': [2]}, {'volumeRecordedAt': [9]}):
            with self.subTest(claim=claim):
                self.assertEqual(check(claim, 'WrongKind', self.source,
                                       out_dir=self.directory)['status'], 'rejected')

    def test_optical_order_requires_same_volume_correct_kinds_and_separated_times(self):
        good = check({'createdAfterVolumeRecord': [4, 3]}, 'OpticalOrder', self.source,
                     out_dir=self.directory)
        self.assertEqual(good['status'], 'verified')
        self.assertEqual(good['axioms'], [])
        self.assertEqual(verify(good, self.source), [])
        self.assertIn('disc T7', good['english'])
        self.assertIn('does not establish that a burn or copy completed', good['english'])
        for args in ([7, 3], [8, 3], [5, 3], [4, 9], [10, 3]):
            with self.subTest(args=args):
                self.assertEqual(check({'createdAfterVolumeRecord': args}, 'WrongOrder',
                                       self.source, out_dir=self.directory)['status'], 'rejected')

    def test_miner_emits_unpaired_filesystem_creation_and_typed_optical_relation(self):
        candidates = [c for _q, c in mine.candidates(self.source)]
        parts = [claims.to_json(p) for c in candidates for p in claims.parts(claims.parse(c))]
        # Row 7 has no modification record on OTHER-VOLUME.
        self.assertIn({'fileCreatedAt': [7]}, parts)
        self.assertIn({'createdAfterVolumeRecord': [4, 3]}, parts)
        self.assertNotIn({'createdAfterVolumeRecord': [7, 3]}, parts)
        self.assertNotIn({'createdAfterVolumeRecord': [5, 3]}, parts)

    def test_complete_mode_covers_a_kind_the_bounded_miner_reports_as_omitted(self):
        rows = [Fact(i, 'fileRenamed', i * 10, 1, i, i + 10000)
                for i in range(1, mine.RESTATE_UP_TO + 2)]
        src = MemorySource(rows)
        self.assertEqual(mine.skipped_kinds(src), {'fileRenamed': len(rows)})
        self.assertEqual(mine.skipped_kinds(src, complete=True), {})
        self.assertEqual(mine.candidates(src), [])
        out = mine.candidates(src, complete=True)
        ids = [p[1][0] for _q, c in out for p in claims.parts(claims.parse(c)) if p[0] == 'renamed']
        self.assertEqual(ids, [r.id for r in rows])

    def test_recovered_modification_only_entries_do_not_invent_creation_or_crash(self):
        src = MemorySource([
            Fact(1, 'fileModified', 100, 1, 10, 20),
            Fact(2, 'fileModified', 100, 1, 11, 21),
            Fact(3, 'tag', 200, 1, 10, 30),
            Fact(4, 'tag', 200, 1, 11, 30),
            Fact(5, 'unallocatedOnDevice', 300, 1, 40, 20),
        ])
        src.string = lambda sid: mine.SAME + 'group' if sid == 30 else str(sid)
        parts = [claims.to_json(p) for _q, c in mine.candidates(src)
                 for p in claims.parts(claims.parse(c))]
        self.assertIn({'fileModifiedAt': [1]}, parts)
        self.assertIn({'fileModifiedAt': [2]}, parts)
        self.assertFalse(any('recoveredOnDevice' in p or 'fileCreatedAt' in p for p in parts))


if __name__ == '__main__':
    unittest.main()
