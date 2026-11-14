"""Public question conversion, private-key isolation and safe investigator outputs."""
import contextlib
import io
import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from agent import run
from agent.brief import investigator_brief
from agent.case import NIST_NAME, NIST_CASE_ID, read_profile, read_question_profile, select_case


class CaseProfiles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.facts = self.write('other.json', {'_meta': {'case': 'Missing Recipe', 'case_id': 'recipe',
                    'time_zone': 'America/Los_Angeles'}, 'strings': {}, 'facts': []})
        self.profile = self.write('context.json', {'name': 'Missing Recipe', 'case_id': 'recipe',
            'brief': 'A recipe disappeared. Establish what the evidence supports.',
            'questions': ['Which recipe files were accessed?'], 'time_zone': 'America/Los_Angeles'})
        self.questions = self.write('questions.json', {'schema_version': 2, 'case_id': 'recipe',
            'title': 'Public recipe investigation', 'time_zone': 'America/Los_Angeles',
            'questions': [{'id': 'Q1', 'prompt': 'Which recipe files were accessed?',
                           'answer_schema': {'type': 'object', 'properties': {'name': {'type': 'string'}}},
                           'match': {'strings': 'casefold'}}]})

    def write(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))
        return path

    @staticmethod
    def finished(*args, **kwargs):
        return {'summary': 'No relevant findings.', 'turns': 1, 'tool_calls': 0,
                'seconds': 0, 'ended': 'success'}

    def call_main(self, argv):
        with patch.object(run, 'ROOT', self.root), \
             patch.object(run, 'run_claude_code', side_effect=self.finished) as claude, \
             patch.object(run, 'run_deepagents', side_effect=self.finished) as deep, \
             contextlib.redirect_stdout(io.StringIO()):
            result = run.main(argv)
        return result, claude, deep

    def assert_generic(self, prompt):
        for value in ('Iaman', 'Spy Conspirator', 'RM#1', 'RM#2', 'RM#3', 'America/New_York'):
            self.assertNotIn(value, prompt)
        self.assertIn('fileCreationRecorded', prompt)
        self.assertIn('do not by themselves imply a reformat', prompt)

    def test_metadata_and_absent_metadata_do_not_inherit_nist(self):
        profile, source = select_case(self.facts)
        self.assertEqual((profile.name, profile.case_id, source), ('Missing Recipe', 'recipe', 'metadata'))
        self.assert_generic(investigator_brief(profile))
        self.facts.write_text(json.dumps({'facts': [], 'strings': {}}))
        profile, source = select_case(self.facts)
        self.assertEqual(source, 'generic')
        self.assertIsNone(profile.case_id)
        self.assert_generic(investigator_brief(profile))

    def test_both_backends_receive_public_questions_without_auto_scoring(self):
        for backend in ('claude-code', 'deepagents'):
            _, claude, deep = self.call_main(['--facts', str(self.facts), '--case-profile', str(self.profile),
                '--questions', str(self.questions), '--backend', backend, '--name', f'dev/{backend}'])
            selected = claude if backend == 'claude-code' else deep
            prompt = selected.call_args.kwargs['prompt']
            self.assertIn('Q1: Which recipe files were accessed?', prompt)
            self.assertIn('Public answer structure:', prompt)
            self.assertIn('Public comparison policy: {"strings": "casefold"}', prompt)
            self.assert_generic(prompt)
            directory = self.root / 'runs' / 'dev' / backend
            result = json.loads((directory / 'results.json').read_text())
            self.assertFalse(result['evaluation']['measured'])
            self.assertEqual((directory / 'prompt.md').read_text(), prompt)

    def test_default_evidence_receives_current_sixty_questions_but_no_key(self):
        self.write('evidence/case_facts.json', {'_meta': {'case': NIST_NAME}, 'facts': [], 'strings': {}})
        _, backend, _ = self.call_main(['--name', 'default'])
        prompt = backend.call_args.kwargs['prompt']
        self.assertIn('Q60: Create a visual diagram', prompt)
        self.assertIn('Q1: What are the hash values', prompt)
        result = json.loads((self.root / 'runs/default/results.json').read_text())
        self.assertFalse(result['evaluation']['measured'])
        self.assertEqual(result['case_id'], NIST_CASE_ID)

    def test_private_reference_never_enters_prompt_and_external_answers_are_explicit(self):
        reference = self.write('key.json', {'schema_version': 2, 'case_id': 'recipe',
            'questions': [{'id': 'Q1', 'prompt': 'Which recipe files were accessed?', 'expected': {'name': 'NEVER_EXPOSE_PRIVATE_REFERENCE'}}]})
        answers = self.write('submitted.json', {'schema_version': 2, 'case_id': 'recipe',
            'answers': [{'question_id': 'Q1', 'status': 'unknown'}]})
        cwd = Path.cwd()
        _, backend, _ = self.call_main(['--facts', str(self.facts), '--name', 'scored',
            '--questions', str(self.questions), '--reference', str(reference), '--answers', str(answers)])
        self.assertNotIn('NEVER_EXPOSE_PRIVATE_REFERENCE', backend.call_args.kwargs['prompt'])
        self.assertNotIn(str(reference), backend.call_args.kwargs['prompt'])
        self.assertEqual(Path.cwd(), cwd)
        result = json.loads((self.root / 'runs/scored/results.json').read_text())
        self.assertEqual(result['question_counts']['unanswered'], 1)
        self.assertTrue(result['evaluation']['measured'])

    def test_no_score_does_not_open_a_private_reference(self):
        self.call_main(['--facts', str(self.facts), '--name', 'unmeasured', '--no-score',
                        '--reference', str(self.root / 'does-not-exist.json')])
        result = json.loads((self.root / 'runs/unmeasured/results.json').read_text())
        self.assertEqual(result['evaluation']['reason'], '--no-score')

    def test_private_reference_cannot_be_used_as_public_profile(self):
        key = self.write('private.json', {'schema_version': 2, 'case_id': 'recipe',
                    'questions': [{'id': 'Q1', 'prompt': 'q', 'expected': 'secret'}]})
        for reader in (read_question_profile, read_profile):
            with self.assertRaises(ValueError):reader(key)
        with patch.object(run, 'ROOT', self.root), patch.object(run, 'run_claude_code') as backend, \
             contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            run.main(['--facts', str(self.facts), '--questions', str(key), '--name', 'bad'])
        backend.assert_not_called()
        self.assertFalse((self.root / 'runs').exists())

    def test_case_conflicts_fail_before_backend(self):
        data = json.loads(self.questions.read_text());data['case_id'] = NIST_CASE_ID
        self.questions.write_text(json.dumps(data))
        with patch.object(run, 'ROOT', self.root), patch.object(run, 'run_claude_code') as backend, \
             contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            run.main(['--facts', str(self.facts), '--questions', str(self.questions), '--name', 'bad'])
        backend.assert_not_called()
        self.assertFalse((self.root / 'runs').exists())

    def test_old_runs_and_unsafe_paths_are_preserved(self):
        directory = run.prepare_run_dir('dev/nested', self.root)
        sentinel = directory / 'original.txt';sentinel.write_text('keep')
        for name in ('dev/nested', '../escape', 'dev/../escape', '/tmp/outside', '.', '', 'a//b', 'C:\\temp\\x'):
            with self.subTest(name=name), self.assertRaises(ValueError):run.prepare_run_dir(name, self.root)
        outside = self.root / 'outside';outside.mkdir()
        (self.root / 'runs/alias').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):run.prepare_run_dir('alias/new', self.root)
        self.assertEqual(sentinel.read_text(), 'keep')

    def test_deepagents_uses_selected_prompt_and_exposes_original_tools(self):
        backend = Mock();backend.invoke.return_value = {'messages': [types.SimpleNamespace(content='done')]}
        create = Mock(return_value=backend)
        deep_module = types.ModuleType('deepagents');deep_module.create_deep_agent = create
        tools_module = types.ModuleType('langchain_core.tools');tools_module.tool = lambda function: function
        with patch.dict('sys.modules', {'deepagents': deep_module, 'langchain_core.tools': tools_module}), \
             patch('agent.tools.Workbench') as bench:
            bench.return_value.conclude.return_value = {'status': 'accepted'}
            run.run_deepagents('test', self.root, str(self.facts), prompt='PUBLIC ONLY')
            tools = {t.__name__: t for t in create.call_args.kwargs['tools']}
            self.assertEqual(set(tools), set(run.INVESTIGATOR_TOOLS))
            tools['conclude']('uncertain', ['A001'])
            bench.return_value.conclude.assert_called_once_with('uncertain', ['A001'])
        self.assertEqual(backend.invoke.call_args.args[0]['messages'][0]['content'], 'PUBLIC ONLY')


if __name__ == '__main__':
    unittest.main()
