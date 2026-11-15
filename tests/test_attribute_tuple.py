"""Atomic typed tuples prove all member types/identities and one source subject."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from checker import check as checker, claims
from checker.catalog import ROLES
from checker.facts import JsonFacts
from extractor.attributes import emit_attribute
from extractor.store import Evidence
from verifier.verify import verify


class AttributeTuple(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ev = Evidence()
        self.attributes = {}
        values = [
            ('product', 'os.product_name', 'Fixture OS'),
            ('version', 'os.version', '7.2'),
            ('build', 'os.build_number', 12345),
            ('root', 'os.system_root', r'C:\FixtureWindows'),
            ('owner', 'os.registered_owner', 'Fixture owner'),
            ('enabled', 'account.enabled', False),
            ('machine', 'machine.account_name', 'FIXTURE-PC'),
            ('count', 'account.count', 2),
        ]
        self.names = [name for name, _, _ in values]
        for name, role, value in values:
            self.emit(name, 'image-A:base-volume:fixture-subject', role, value)
        self.emit('other_build', 'image-B:base-volume:fixture-subject', 'os.build_number', 12345)
        self.emit('snapshot_count', 'image-A:vss:fixture-subject', 'account.count', 2)
        self.path = self.root / 'facts.json'
        self.ev.write_json(self.path, {})
        self.source = JsonFacts(self.path)
        self.sequence = 0

    def emit(self, name, subject, role, value):
        identity = emit_attribute(self.ev, subject, role, value, 100_000_000,
                                  artifact='synthetic source ' + name)
        self.attributes[name] = identity, role

    def row(self, name):
        identity, role = self.attributes[name]
        rows = {f.kind: f.id for f in self.source.all() if self.source.string(f.obj) == identity}
        return [rows['attributeSubject'], rows[ROLES[role].kind], rows[ROLES[role].value_kind], role]

    def claim(self, *names):
        return {'attributeTuple': [self.row(name) for name in names]}

    def certify(self, claim, accepted=True):
        self.sequence += 1
        with patch('checker.check.run_kernel', wraps=checker.run_kernel) as kernel:
            result = checker.check(claim, f'Tuple{self.sequence}', self.source, out_dir=self.root)
        self.assertTrue(kernel.called, 'semantic type and association checks must reach Lean')
        self.assertEqual(result['status'], 'verified' if accepted else 'rejected', result)
        if accepted:
            self.assertEqual(result['trust_tier'], 'kernel')
            self.assertEqual(result['axioms'], [])
            self.assertEqual(result['rules'], ['R34'])
            self.assertEqual(len(result['parts']), 1)
            self.assertEqual(verify(result, self.source), [])
        return result

    def test_three_native_types_in_one_atomic_certificate(self):
        raw = self.claim('version', 'build', 'enabled')
        parsed = claims.parse(raw)
        self.assertEqual(claims.to_json(parsed), raw)
        self.assertEqual(claims.parts(parsed), [parsed])
        self.assertEqual(claims.fact_ids(parsed), [fid for row in raw['attributeTuple'] for fid in row[:3]])
        cert = self.certify(raw)
        self.assertIn("'7.2'", cert['english'])
        self.assertIn('12345', cert['english'])
        self.assertIn('False', cert['english'])
        self.assertIn('exactly the same scoped source subject', cert['english'])
        self.assertIn('not personal attribution', cert['english'])

    def test_all_eight_members_are_checked_and_order_is_preserved(self):
        raw = self.claim(*self.names)
        cert = self.certify(raw)
        self.assertEqual(len(cert['cited_facts']), 24)
        self.assertEqual(cert['claim'], raw)
        # The last member cannot escape the conjunction's source-subject checks.
        raw['attributeTuple'][-1] = self.row('snapshot_count')
        self.certify(raw, accepted=False)

    def test_mixed_subjects_with_equal_values_are_refused(self):
        self.certify(self.claim('product', 'other_build'), accepted=False)

    def test_exact_role_and_value_kinds_cannot_be_reassigned(self):
        raw = self.claim('product', 'version')
        raw['attributeTuple'][1][3] = 'os.system_root'
        self.certify(raw, accepted=False)
        raw = self.claim('product', 'build')
        raw['attributeTuple'][1][2] = self.row('version')[2]
        self.certify(raw, accepted=False)

    def test_same_logical_subject_does_not_allow_mixed_attribute_identity(self):
        raw = self.claim('product', 'version')
        raw['attributeTuple'][1][0] = self.row('root')[0]
        self.certify(raw, accepted=False)

    def test_tuple_syntax_bounds_duplicate_roles_and_malformed_rows(self):
        good = self.row('version')
        for rows in ([], [good], [good] * 9, [good, good],
                     [good, self.row('other_build'), self.row('build')],
                     [good, None], [good, {}], [good, [1, 2, 3]],
                     [good, [1, 2, 3, 'os.version', 4]]):
            with self.subTest(rows=rows), self.assertRaises(claims.ClaimError):
                claims.parse({'attributeTuple': rows})
        for value in (True, -1, 1.0, '1', 2**63, None, [1]):
            raw = self.claim('product', 'version')
            raw['attributeTuple'][1][1] = value
            with self.subTest(value=value), self.assertRaises(claims.ClaimError):
                claims.parse(raw)
        for role in ('unreviewed.role', 'both', {}, None, 12):
            raw = self.claim('product', 'version')
            raw['attributeTuple'][1][3] = role
            with self.subTest(role=role), self.assertRaises(claims.ClaimError):
                claims.parse(raw)

    def test_missing_source_id_and_invalid_last_value_are_not_hidden(self):
        raw = self.claim('product', 'build')
        raw['attributeTuple'][1][2] = 999999
        with patch('checker.check.run_kernel', side_effect=AssertionError('missing source must not run')):
            result = checker.check(raw, 'MissingTupleValue', self.source, out_dir=self.root)
        self.assertEqual(result['status'], 'rejected')
        self.assertEqual(result['proof_gap']['requirements'][0]['category'], 'missing_record')
        raw = self.claim(*self.names)
        data = json.loads(self.path.read_text())
        value = next(row for row in data['facts'] if row['id'] == raw['attributeTuple'][-1][2])
        data['strings'][str(value['aux'])] = '02'
        self.path.write_text(json.dumps(data))
        self.source = JsonFacts(self.path)
        with patch('checker.check.run_kernel', side_effect=AssertionError('malformed typed value must not run')):
            result = checker.check(raw, 'MalformedTupleValue', self.source, out_dir=self.root)
        self.assertEqual(result['status'], 'rejected')

    def test_replay_rejects_dropped_members_relabeling_and_copied_value_tampering(self):
        cert = self.certify(self.claim('product', 'version', 'build'))
        for change in ('drop', 'role', 'value', 'english'):
            bad = copy.deepcopy(cert)
            if change == 'drop':
                bad['claim']['attributeTuple'].pop()
            elif change == 'role':
                bad['claim']['attributeTuple'][-1][3] = 'account.count'
            elif change == 'value':
                bad['cited_facts'][-1]['aux_text'] = '54321'
            else:
                bad['english'] = 'All questions have been answered completely.'
            with self.subTest(change=change):
                self.assertTrue(verify(bad, self.source))

    def test_tuple_inside_both_remains_one_atomic_part_and_cites_all_members(self):
        tuple_claim = self.claim('product', 'version')
        other = {'attributeRecorded': self.row('build')}
        combined = claims.parse({'both': [tuple_claim, other]})
        self.assertEqual(len(claims.parts(combined)), 2)
        self.assertEqual(claims.to_json(combined), {'both': [tuple_claim, other]})
        self.assertEqual(len(claims.fact_ids(combined)), 9)


if __name__ == '__main__':
    unittest.main()
