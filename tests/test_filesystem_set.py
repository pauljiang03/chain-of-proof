"""Exact declared-file-set count and allocation aggregation; no reader summary proof."""
import copy
import re
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from checker import check as checker, claims
from checker.facts import Fact, FactSource, KINDS
from verifier.verify import verify


class Source(FactSource):
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows

    def get(self, ids):
        return {f.id: f for f in self.rows if f.id in ids}

    def string(self, sid):
        return {10: 'image-A/base/volume-17/executable-set',
                20: 'image-A/vss-copy-B/volume-17/executable-set',
                30: 'image-B/base/volume-17/executable-set',
                99: 'completed namespace traversal; distinct .exe members with MZ headers',
                101: 'image-A/base/volume-17/MFT-42-sequence-3',
                102: 'image-A/base/volume-17/MFT-43-sequence-4'}.get(sid, str(sid))


def row(fid, kind, obj=10, aux=99):
    return Fact(fid, kind, 123456, 1, obj, aux,
                {'image': 'image-A', 'source_variant': 'base-volume',
                 'timestamp_semantics': 'examination_observation', 'artifact': 'fixture MFT'})


class FilesystemSet(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.source = Source([row(1, 'filesystemSet'),
                              row(2, 'filesystemMemberDeleted', aux=101),
                              row(3, 'filesystemMemberAllocated', aux=102)])
        self.sequence = 0

    def claim(self, count=2, answer=False, declaration=1):
        return {'filesystemSetDeleted': [declaration, count, answer]}

    def certify(self, raw=None, accepted=True):
        self.sequence += 1
        with patch.object(checker, 'run_kernel', wraps=checker.run_kernel) as kernel:
            cert = checker.check(raw or self.claim(), f'Set{self.sequence}', self.source,
                                 out_dir=Path(self.tmp.name))
        self.assertTrue(kernel.called)
        self.assertEqual(cert['status'], 'verified' if accepted else 'rejected', cert)
        if accepted:
            self.assertEqual(cert['axioms'], [])
            self.assertEqual(cert['trust_tier'], 'kernel')
            self.assertEqual(verify(cert, self.source), [])
        return cert

    def test_counterexample_and_all_deleted_are_kernel_checked(self):
        cert = self.certify()
        self.assertEqual([f['id'] for f in cert['cited_facts']], [1, 2, 3])
        self.assertIn('not all members are marked deleted', cert['english'])
        self.assertIn('not all files', cert['english'])
        self.certify(self.claim(answer=True), accepted=False)
        self.source.rows[2] = replace(self.source.rows[2], kind='filesystemMemberDeleted')
        self.certify(self.claim(answer=True))
        self.certify(self.claim(answer=False), accepted=False)

    def test_wrong_count_omission_duplicate_and_foreign_set_fail(self):
        self.certify(self.claim(count=1), accepted=False)
        self.source.rows.append(row(4, 'filesystemMemberDeleted', aux=101))
        self.certify(self.claim(count=3), accepted=False)
        self.source.rows.pop()
        self.source.rows[2] = replace(self.source.rows[2], obj=20)
        self.certify(self.claim(count=2), accepted=False)
        self.certify(self.claim(count=1, answer=False), accepted=False)
        self.certify(self.claim(count=1, answer=True))

    def test_distinct_sets_and_snapshots_are_not_merged(self):
        self.source.rows += [row(4, 'filesystemSet', obj=20),
                             row(5, 'filesystemMemberAllocated', obj=20, aux=101),
                             row(6, 'filesystemSet', obj=30),
                             row(7, 'filesystemMemberDeleted', obj=30, aux=101)]
        cert = self.certify()
        self.assertEqual([f['id'] for f in cert['cited_facts']], [1, 2, 3])
        self.certify(self.claim(count=1, declaration=4))
        self.certify(self.claim(count=1, answer=True, declaration=6))
        self.certify(self.claim(count=4), accepted=False)

    def test_unknown_flag_blocks_both_boolean_results(self):
        self.source.rows[2] = replace(self.source.rows[2], kind='filesystemMemberUnknown')
        for answer in (True, False):
            cert = self.certify(self.claim(answer=answer), accepted=False)
            self.assertEqual(cert['proof_gap']['requirements'][0]['category'], 'missing_record')
            self.assertEqual(cert['proof_gap']['requirements'][0]['observed']['unknown_flag_ids'], [3])

    def test_declaration_kind_identity_and_duplicate_declaration_checked(self):
        original = self.source.rows[0]
        self.source.rows[0] = replace(original, kind='attributeSubject')
        self.certify(accepted=False)
        self.source.rows[0] = replace(original, aux=0)
        self.certify(accepted=False)
        self.source.rows[0] = original
        self.source.rows.append(replace(original, id=4))
        self.certify(accepted=False)

    def test_syntax_bounds_and_atomic_standalone(self):
        for raw in (self.claim(count=0), self.claim(count=257), self.claim(answer=1),
                    self.claim(declaration=True), self.claim(count=True),
                    {'both': [self.claim(), {'usbConnected': [1]}]}):
            with self.assertRaises(claims.ClaimError):
                claims.parse(raw)
        parsed = claims.parse(self.claim())
        self.assertEqual(claims.parts(parsed), [parsed])
        self.assertEqual(claims.to_json(parsed), self.claim())
        self.source.rows = [self.source.rows[0]]
        self.certify(self.claim(count=1), accepted=False)

    def test_maximum_is_checked_without_silent_truncation(self):
        self.source.rows = [row(1, 'filesystemSet')] + [
            row(i + 2, 'filesystemMemberDeleted', aux=1000+i) for i in range(256)]
        self.certify(self.claim(count=256, answer=True))
        self.source.rows.append(row(999, 'filesystemMemberDeleted', aux=1999))
        with patch.object(checker, 'run_kernel') as kernel:
            result = checker.check(self.claim(count=256, answer=True), 'Oversize', self.source,
                                   out_dir=Path(self.tmp.name))
        kernel.assert_not_called()
        self.assertIn('no partial set', result['reason'])

    def test_replay_binds_added_removed_changed_and_saved_members(self):
        cert = self.certify()
        altered = copy.deepcopy(cert)
        altered['cited_facts'].pop()
        self.assertTrue(verify(altered, self.source))
        altered = copy.deepcopy(cert)
        altered['claim']['filesystemSetDeleted'][2] = True
        self.assertTrue(verify(altered, self.source))
        original = list(self.source.rows)
        for changed in (original + [row(4, 'filesystemMemberDeleted', aux=103)],
                        original[:2],
                        [original[0], original[1], replace(original[2], obj=20)]):
            self.source.rows = changed
            self.assertTrue(verify(cert, self.source))
        self.source.rows = original
        with patch.object(claims, 'MAX_CENSUS', 2), patch('verifier.verify.run_kernel') as kernel:
            errors = verify(cert, self.source)
        kernel.assert_not_called()
        self.assertIn('cannot bind the complete cited evidence', errors[0])

    def test_support_resolution_never_checks_or_repairs_proposed_values(self):
        self.assertEqual(claims.filesystem_set_support_ids(1, self.source), [1, 2, 3])
        self.assertEqual(claims.filesystem_set_support_ids(999, self.source), [999])
        proposed = self.claim(count=77, answer=True)
        before = copy.deepcopy(proposed)
        self.assertEqual(claims.filesystem_set_support_ids(proposed['filesystemSetDeleted'][0], self.source), [1, 2, 3])
        self.assertEqual(proposed, before)
        self.source.rows[0] = replace(self.source.rows[0], kind='attributeSubject')
        self.assertEqual(claims.filesystem_set_support_ids(1, self.source), [1, 2, 3])

    def test_duplicate_source_ids_fail_closed_before_kernel(self):
        self.source.rows.append(self.source.rows[1])
        with patch.object(checker, 'run_kernel') as kernel:
            result = checker.check(self.claim(count=3), 'Duplicate', self.source, out_dir=Path(self.tmp.name))
        kernel.assert_not_called()
        self.assertEqual(result['status'], 'rejected')
        self.assertIn('unique source fact IDs', result['reason'])

    def test_kind_order_matches_lean_and_sql_exactly(self):
        root = Path(__file__).resolve().parents[1]
        lean = (root / 'lean/ChainOfProof/Facts.lean').read_text()
        lean = lean.split('inductive Kind where', 1)[1].split('deriving DecidableEq', 1)[0]
        lean_kinds = re.findall(r'\|\s*([A-Za-z][A-Za-z0-9_]*)', re.sub(r'--[^\n]*', '', lean))
        sql = (root / 'extractor/schema.sql').read_text().split('CHECK (kind IN (', 1)[1].split('))', 1)[0]
        sql_kinds = re.findall(r"'([^']+)'", sql)
        self.assertEqual(list(KINDS), lean_kinds)
        self.assertEqual(list(KINDS), sql_kinds)

    def test_generic_timestamp_order_keeps_membership_examination_meaning(self):
        self.source.rows[2] = replace(self.source.rows[2], t=200000)
        cert = self.certify({'before': [2, 3]})
        self.assertIn('examination record', cert['english'])
        self.assertNotIn('the deletion of', cert['english'])


if __name__ == '__main__':
    unittest.main()
