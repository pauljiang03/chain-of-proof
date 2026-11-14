"""Neutral baseline integration, explicit case binding and preserved outputs."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from eval import baseline


class BaselineCases(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.facts = self.write('facts.json', {'_meta': {'case': 'Independent Case', 'case_id': 'other',
                            'time_zone': 'America/Los_Angeles'}, 'facts': [], 'strings': {}})
        self.questions = self.write('public.json', {'schema_version': 2, 'case_id': 'other',
            'time_zone': 'America/Los_Angeles', 'questions': [{'id': 'Q1', 'prompt': 'What is recorded?',
            'answer_schema': {'type': 'object', 'properties': {'present': {'type': 'boolean'}}}}]})
        self.reference = self.write('key.json', {'schema_version': 2, 'case_id': 'other',
            'questions': [{'id': 'Q1', 'prompt': 'What is recorded?', 'expected': {'present': True}}]})
        self.answers = self.write('external.json', {'schema_version': 2, 'case_id': 'other',
            'answers': [{'question_id': 'Q1', 'status': 'answered', 'answer': {'present': True}}]})
        self.certs = self.root / 'output' / 'certs'
        self.run = self.root / 'output' / 'run.json'
        self.output = self.root / 'output' / 'results.json'
        self.argv = ['--facts', str(self.facts), '--certs', str(self.certs), '--run', str(self.run),
                     '--out', str(self.output)]

    def write(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value))
        return path

    def invoke(self, extra=()):
        with patch.object(baseline.miner, 'mine', return_value=[]) as miner, \
             contextlib.redirect_stdout(io.StringIO()):
            result = baseline.main(self.argv + list(extra))
        return result, miner

    def evaluation_args(self):
        return ['--reference', str(self.reference), '--questions', str(self.questions)]

    def test_custom_case_is_not_measured_without_explicit_contract(self):
        result, miner = self.invoke(['--complete'])
        self.assertEqual(result, 0)
        self.assertTrue(miner.call_args.kwargs['complete'])
        measured = json.loads(self.output.read_text())
        self.assertFalse(measured['evaluation']['measured'])
        self.assertFalse(measured['gate_regression']['measured'])
        data = json.loads(self.run.read_text())
        self.assertEqual(data['case']['case_id'], 'other')
        self.assertEqual(data['case']['name'], 'Independent Case')
        self.assertFalse((self.output.parent / 'answers.json').exists())

    def test_external_structured_answers_use_the_neutral_contract(self):
        result, _ = self.invoke(self.evaluation_args() + ['--answers', str(self.answers)])
        self.assertEqual(result, 0)
        measured = json.loads(self.output.read_text())
        self.assertEqual(measured['question_counts']['fully_correct'], 1)
        self.assertIn('no Lean certification', measured['evaluation']['answer_origin'])
        self.assertFalse((self.output.parent / 'verification.json').exists())

    def test_non_nist_case_never_falls_through_to_nist_adapter(self):
        with patch.object(baseline.miner, 'mine') as miner, \
             contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            baseline.main(self.argv + self.evaluation_args() + ['--adapter', 'nist'])
        miner.assert_not_called()
        self.assertFalse(self.run.exists())

    def test_reference_alone_cannot_select_hidden_questions(self):
        with patch.object(baseline.miner, 'mine') as miner, \
             contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            baseline.main(self.argv + ['--reference', str(self.reference)])
        miner.assert_not_called()
        self.assertFalse(self.certs.exists())

    def test_reference_and_public_profile_without_adapter_are_not_measured(self):
        self.invoke(self.evaluation_args())
        result = json.loads(self.output.read_text())
        self.assertFalse(result['evaluation']['measured'])
        self.assertIn('adapter', result['evaluation']['reason'])

    def test_explicit_gate_is_separate_from_findings_and_coverage(self):
        labels = self.write('probes.json', {'case_id': 'other', 'facts': {}, 'claims': [
            {'id': 'true', 'label': True, 'claim': {}},
            {'id': 'false', 'label': False, 'claim': {}, 'ask': 'q', 'basis': 'b'}]})
        with patch.object(baseline.gate, 'score_gate', return_value=[{'id': 'P0001', 'label': False,
                'verdict': 'rejected', 'as_expected': True}]) as check:
            self.invoke(['--labeled-claims', str(labels)])
        probes = check.call_args.args[0]['claims']
        self.assertEqual([c['label'] for c in probes], [False])
        self.assertEqual(check.call_args.args[4], self.certs / 'gate-probes')
        self.assertEqual(json.loads(self.run.read_text())['findings'], [])
        self.assertEqual(json.loads(self.output.read_text())['gate_regression']['false_claims_rejected'], 1)

    def test_existing_outputs_and_aliases_are_refused(self):
        self.certs.mkdir(parents=True)
        sentinel = self.certs / 'original.lean'
        sentinel.write_text('keep')
        with patch.object(baseline.miner, 'mine') as miner, \
             contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            baseline.main(self.argv)
        miner.assert_not_called()
        self.assertEqual(sentinel.read_text(), 'keep')
        sentinel.unlink(); self.certs.rmdir()
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            baseline.main(self.argv + ['--out', str(self.run)])
        self.assertFalse(self.run.exists())


if __name__ == '__main__':
    unittest.main()
