"""A/B share immutable candidates and literal leaves; C uses the same projector."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from comparison.ablation.projection import project_a, project_b, project_c
from tests.test_answer_projection import Source, bind, candidate, public


def replay(row, status):
    return {**row, 'status': status, 'checker_status': 'verified' if status == 'verified' else 'rejected',
            'verification': {'passed': True} if status == 'verified' else None}


class AblationProjection(unittest.TestCase):
    def setUp(self):
        self.source = Source()
        self.good = candidate('P1', {'usbConnected': [1]})
        self.bad = candidate('P2', {'deviceHolds': [1, 2]})
        self.count = candidate('P3', {'exactly': ['usbInsert', 55]})
        self.rows = [self.good, self.bad, self.count]
        self.bindings = [bind(self.good, 'devices', ['devices', 0, 'serial'], 'device_serial'),
                         bind(self.bad, 'devices', ['devices', 1, 'serial'], 'device_serial'),
                         bind(self.bad, 'devices', ['devices', 1, 'volume'], 'volume'),
                         bind(self.count, 'count', [], 'count')]

    def test_b_only_filters_original_candidates_without_evidence_access_or_new_model(self):
        before = deepcopy((self.rows, self.bindings))
        a = project_a(public(), self.rows, self.bindings, self.source)
        saved = deepcopy(a)
        with patch.object(self.source, 'get', side_effect=AssertionError('B cannot repair from evidence')), \
             patch('checker.check.run_kernel', side_effect=AssertionError('projection cannot call kernel')):
            b = project_b(a, [replay(self.good, 'verified'), replay(self.bad, 'rejected'), replay(self.count, 'rejected')])
        self.assertEqual(a, saved)
        self.assertEqual((self.rows, self.bindings), before)
        self.assertEqual(a['submission']['answers'][1]['answer'], 55)
        self.assertEqual(b['submission']['answers'][1]['status'], 'unknown')
        self.assertEqual(b['submission']['answers'][0]['answer'], {'devices': [{'serial': 'DEVICE-A'}]})
        self.assertEqual(len(b['dropped']), 3)
        self.assertEqual(b['model_calls'], 0)
        self.assertIs(b['source_repair'], False)
        self.assertEqual(b['projection']['projection_sha256'], a['projection']['projection_sha256'])

    def test_c_has_the_same_output_as_b_for_the_same_accepted_claims_and_bindings(self):
        a = project_a(public(), self.rows, self.bindings, self.source)
        statuses = ['verified', 'rejected', 'rejected']
        b = project_b(a, [replay(row, status) for row, status in zip(self.rows, statuses)])
        c = project_c(public(), [dict(row, status=status) for row, status in zip(self.rows, statuses)], self.bindings, self.source)
        self.assertEqual(b['submission'], c['submission'])
        self.assertEqual(b['leaves'], c['leaves'])
        self.assertEqual(c['certification'], 'not_performed_by_projector')

    def test_replay_tampering_omission_order_and_forged_acceptance_receipt_are_refused(self):
        a = project_a(public(), self.rows, self.bindings, self.source)
        rows = [replay(row, 'verified') for row in self.rows]
        mutations = [rows[:-1], list(reversed(rows)),
                     [dict(rows[0], claim={'usbConnected': [3]}), *rows[1:]],
                     [dict(rows[0], verification={'passed': False}), *rows[1:]]]
        for changed in mutations:
            with self.subTest(rows=changed), self.assertRaises(ValueError):
                project_b(a, changed)
        changed_a = deepcopy(a)
        changed_a['submission']['answers'][0]['answer'] = 'repaired'
        with self.assertRaisesRegex(ValueError, 'unfiltered projection'):
            project_b(changed_a, rows)

    def test_whole_compound_filter_removes_all_of_its_bindings(self):
        compound = candidate('BOTH', {'both': [{'usbConnected': [1]}, {'before': [5, 4]}]})
        bindings = [bind(compound, 'devices', ['devices', 0, 'serial'], 'device_serial'),
                    bind(compound, 'order', [], 'precedes_beyond_uncertainty', part=1)]
        a = project_a(public(), [compound], bindings, self.source)
        b = project_b(a, [replay(compound, 'rejected')])
        self.assertEqual(len(a['leaves']), 2)
        self.assertEqual(len(b['dropped']), 2)
        self.assertTrue(all(row['status'] == 'unknown' for row in b['submission']['answers']))

    def test_filtering_cannot_reveal_values_hidden_by_a_frozen_collision(self):
        wrong = candidate('WRONG', {'usbConnected': [3]})
        path = ['devices', 0, 'serial']
        bindings = [bind(self.good, 'devices', path, 'device_serial'),
                    bind(wrong, 'devices', path, 'device_serial')]
        a = project_a(public(), [self.good, wrong], bindings, self.source)
        b = project_b(a, [replay(self.good, 'verified'), replay(wrong, 'rejected')])
        c = project_c(public(), [replay(self.good, 'verified'), replay(wrong, 'rejected')], bindings, self.source)
        self.assertEqual(a['submission']['answers'][0]['status'], 'unknown')
        self.assertEqual(b['submission'], a['submission'])
        self.assertEqual(c['submission'], a['submission'])
        self.assertEqual(b['leaves'], [])
        self.assertEqual(b['conflicts'], a['conflicts'])
        self.assertEqual([row['reason'] for row in b['dropped']], ['frozen_projection_conflict'] * 2)
        self.assertEqual([row['candidate_admitted'] for row in b['dropped']], [True, False])
        self.assertEqual(b['projection'], a['projection'])


if __name__ == '__main__':
    unittest.main()
