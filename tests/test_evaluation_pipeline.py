"""Certificates must independently reverify before any answer adaptation or scoring."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from checker.check import check
from checker.facts import open_source
from eval.pipeline import Plan, evaluate, main


ROOT = Path(__file__).resolve().parent.parent
FACTS = ROOT / 'fixtures' / 'sample_facts.json'
CASE = 'nist-cfreds-data-leakage'


class EvaluationPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.cert = check({'searched': [3100]}, 'Pipeline', open_source(FACTS),
                         out_dir=Path(cls.temp.name))
        if cls.cert['status'] != 'verified':
            raise AssertionError(cls.cert)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.run = {'case': {'case_id': CASE}, 'findings': [copy.deepcopy(self.cert)]}
        self.public = {'schema_version': 2, 'case_id': CASE,
                       'questions': [{'id': 'Q16', 'prompt': 'Which search?', 'answer_schema': {}}]}
        reference = {'schema_version': 2, 'case_id': CASE, 'questions': [{'id': 'Q16',
            'prompt': 'Which search?', 'expected': {'searches': [{'timestamp': '2015-03-23T13:56:40Z',
            'keyword': 'sample data leakage methods', 'browser': '(none)'}]}}]}
        self.plan = Plan(CASE, reference, self.public, 'nist')

    def call(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return evaluate(self.plan, self.run, self.root / 'answers.json', self.root / 'results.json',
                            facts_path=FACTS, verification_output=self.root / 'verification.json')

    def test_verified_bundle_reaches_neutral_answer_scoring(self):
        result = self.call()
        self.assertTrue(json.loads((self.root / 'verification.json').read_text())['passed'])
        self.assertEqual(result['question_counts']['fully_correct'], 1)
        self.assertTrue((self.root / 'answers.json').exists())

    def test_status_and_saved_hash_cannot_authenticate_forged_copied_values(self):
        self.run['findings'][0]['cited_facts'][0]['obj_text'] = 'forged search'
        with patch('eval.nist_answers.generate') as adapt:
            with self.assertRaisesRegex(ValueError, 'verification failed'):
                self.call()
        adapt.assert_not_called()
        verification = json.loads((self.root / 'verification.json').read_text())
        self.assertFalse(verification['passed'])
        self.assertFalse((self.root / 'answers.json').exists())
        self.assertFalse((self.root / 'results.json').exists())

    def test_duplicate_certificate_ids_never_reach_adapter(self):
        self.run['findings'].append(copy.deepcopy(self.run['findings'][0]))
        with patch('eval.nist_answers.generate') as adapt, self.assertRaisesRegex(ValueError, 'duplicate'):
            self.call()
        adapt.assert_not_called()
        self.assertFalse((self.root / 'results.json').exists())

    def test_existing_evaluation_artifacts_are_preserved(self):
        path = self.root / 'verification.json';path.write_text('keep')
        with self.assertRaisesRegex(ValueError, 'overwrite'):
            self.call()
        self.assertEqual(path.read_text(), 'keep')

    def cli(self, output):
        for name, value in [('run', self.run), ('public', self.public), ('reference', self.plan.reference)]:
            (self.root / f'{name}.json').write_text(json.dumps(value))
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return main(['--run', str(self.root / 'run.json'), '--facts', str(FACTS),
                         '--questions', str(self.root / 'public.json'),
                         '--reference', str(self.root / 'reference.json'),
                         '--adapter', 'nist', '--out', str(output)])

    def test_existing_run_cli_verifies_and_writes_three_artifacts(self):
        output = self.root / 'evaluation'
        self.assertEqual(self.cli(output), 0)
        self.assertEqual({p.name for p in output.iterdir()},
                         {'answers.json', 'results.json', 'verification.json'})
        result = json.loads((output / 'results.json').read_text())
        self.assertEqual(result['question_counts']['fully_correct'], 1)
        self.assertIn('sha256', result['inputs']['run'])

    def test_existing_run_cli_refuses_existing_directory_before_verification(self):
        output = self.root / 'evaluation'; output.mkdir()
        with patch('eval.pipeline.verify_run') as verify, self.assertRaises(SystemExit) as error:
            self.cli(output)
        self.assertEqual(error.exception.code, 2)
        verify.assert_not_called()
        self.assertEqual(list(output.iterdir()), [])

    def test_existing_run_cli_keeps_failure_diagnostics_without_answers_or_scores(self):
        self.run['findings'][0]['cited_facts'][0]['obj_text'] = 'forged search'
        output = self.root / 'evaluation'
        with self.assertRaises(SystemExit) as error:
            self.cli(output)
        self.assertEqual(error.exception.code, 2)
        self.assertEqual({p.name for p in output.iterdir()}, {'verification.json'})
        self.assertFalse(json.loads((output / 'verification.json').read_text())['passed'])


if __name__ == '__main__':
    unittest.main()
