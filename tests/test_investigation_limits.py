"""Finding-reference budgets and best-effort automatic work-note tracking."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent.case import CaseProfile
from agent.investigation import Investigation, MAX_FINDING_IDS, MAX_ITEMS
from agent.tools import Workbench


class InvestigationLimits(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.run = self.root / 'run'
        self.plan = Investigation(self.run)
        self.plan.initialize(CaseProfile('Fixture', 'Public fixture', ('Which record?',)))

    def test_finding_budget_is_separate_and_failure_preserves_saved_plan(self):
        self.assertGreater(MAX_FINDING_IDS, MAX_ITEMS)
        ids = [f'A{i:04d}' for i in range(MAX_FINDING_IDS)]
        # Certificate linkage has its own tests; isolate the list budget here.
        with patch('agent.investigation.current_certificates', return_value={}):
            first = self.plan.update('Q1', finding_ids=ids[:MAX_ITEMS + 1])
            self.assertEqual(len(first['questions'][0]['finding_ids']), MAX_ITEMS + 1)
            state = self.plan.update('Q1', finding_ids=ids[MAX_ITEMS + 1:])
            self.assertEqual(state['questions'][0]['finding_ids'], ids)
            self.assertEqual(self.plan.snapshot(), state)
            saved = self.plan.path.read_bytes()
            for arguments in ({'finding_ids': ['A99999']},
                              {'finding_ids': ids + ['A99999']},
                              {'searched': ['note'] * (MAX_ITEMS + 1)},
                              {'unresolved': ['note'] * (MAX_ITEMS + 1)}):
                with self.assertRaises(ValueError):
                    self.plan.update('Q1', **arguments)
                self.assertEqual(self.plan.path.read_bytes(), saved)

    def _bench(self):
        facts = self.root / 'facts.json'
        facts.write_text(json.dumps({'strings': {'1': 'fixture'}, 'facts': [
            {'id': 1, 'kind': 'usbInsert', 't': 0, 'res': 0,
             'obj': 1, 'aux': 1, 'prov': {'artifact': 'fixture'}}]}))
        bench = Workbench(facts, self.run)
        self.addCleanup(bench._db.close)
        return bench

    @staticmethod
    def _saved_check(claim, finding_id, source, question, out_dir, proposer):
        # Synthetic proof execution, retaining actual certificate/log writes.
        row = {'finding_id': finding_id, 'status': 'verified', 'claim': claim,
               'question': question, 'english': 'Fixture observation.',
               'cited_facts': [], 'rules': [], 'strength': 'strong',
               'trust_tier': 'kernel', 'axioms': []}
        (out_dir / (finding_id + '.json')).write_text(json.dumps(row))
        with (out_dir / 'proposals.jsonl').open('a') as stream:
            stream.write(json.dumps(row) + '\n')
        return row

    def test_accepted_certificate_survives_history_cap_tracking_failure(self):
        bench = self._bench()
        saved = self.plan.path.read_bytes()
        with patch('agent.tools.checker.check', side_effect=self._saved_check), \
                patch('agent.investigation.MAX_HISTORY', 1):
            result = bench.check('Q1', {'usbConnected': [1]})
        self.assertEqual(result['status'], 'verified')
        self.assertEqual(result['finding_id'], 'A001')
        self.assertEqual(result['tracking_warning']['error_type'], 'ValueError')
        self.assertEqual(result['tracking_warning']['status'], 'unverified')
        self.assertEqual(self.plan.path.read_bytes(), saved)
        certificate = json.loads((self.run / 'A001.json').read_text())
        self.assertEqual(certificate['status'], 'verified')
        self.assertNotIn('tracking_warning', certificate)
        audit = json.loads((self.run / 'audit.jsonl').read_text().splitlines()[-1])
        self.assertEqual(audit['result'], result)
        self.assertEqual(audit['outcome'], 'success')

    def test_accepted_certificate_survives_plan_write_failure(self):
        bench = self._bench()
        saved = self.plan.path.read_bytes()
        with patch('agent.tools.checker.check', side_effect=self._saved_check), \
                patch('agent.investigation.atomic_json', side_effect=OSError('fixture write failure')):
            result = bench.check('Q1', {'usbConnected': [1]})
        self.assertEqual(result['status'], 'verified')
        self.assertEqual(result['tracking_warning']['error_type'], 'OSError')
        self.assertTrue((self.run / 'A001.json').is_file())
        self.assertEqual(self.plan.path.read_bytes(), saved)


if __name__ == '__main__':
    unittest.main()
