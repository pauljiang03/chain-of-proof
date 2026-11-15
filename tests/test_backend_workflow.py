"""CLI intake -> tool collection -> new run -> report, using a synthetic parser/model.

Only model execution and image parsing are replaced. Evidence snapshots, public
profiles, the investigator runner, tool audits, Lean checks and reports are real.
"""
import contextlib
import io
import json
from pathlib import Path
from unittest.mock import patch

from agent import run
from agent.case import select_case
from agent.tools import Workbench
from app import cli
from app.jobs import JobManager
from app.report import render_html
from tests.test_intake import IntakeFixture


class InlineManager:
    def __init__(self, root, backend):
        self.root, self.backend = root, backend

    def start(self, payload, *, case_profile=None, question_profile=None, resume_from=None, intake_config=None):
        spec = JobManager(self.root)._prepare(payload, case_profile, question_profile)
        profile = self.root / (spec['name'].replace('/', '_') + '-public.json')
        profile.write_text(json.dumps(spec['profile']))
        args = ['--name', spec['name'], '--facts', spec['facts'], '--case-profile', str(profile),
                '--backend', spec['backend'], '--model', spec['model'], '--minutes', str(spec['minutes']), '--no-score']
        for flag, value in (('--questions', question_profile), ('--resume-from', resume_from), ('--intake-config', intake_config)):
            if value:
                args += [flag, str(value)]
        with patch.object(run, 'ROOT', self.root), patch.object(run, 'run_deepagents', side_effect=self.backend):
            code = run.main(args)
        if code:
            raise AssertionError('Synthetic investigation failed')
        return {'name': spec['name'], 'status': 'completed'}

    def get_run(self, name):
        value = json.loads((self.root / 'runs' / name / 'run.json').read_text())
        return {'name': name, 'status': 'completed', 'run': value}

    def report(self, name, fmt):
        data = self.get_run(name)['run']
        return render_html(data).encode(), 'text/html', 'report.html'

    def close(self):
        pass


class BackendWorkflow(IntakeFixture):
    def setUp(self):
        super().setUp()
        self.root = self.root.resolve()
        self.manifest_file = self.root / 'manifest.json'
        self.manifest_file.write_text(json.dumps(self.manifest))
        self.stages = []

    def backend(self, model, directory, facts, **kwargs):
        bench = Workbench(facts, directory)
        self.stages.append(bench.plan())
        kinds = bench.sql('SELECT id, kind FROM facts ORDER BY id')['rows']
        for fid, kind in kinds:
            form = {'fileSeen': 'fileRecorded', 'systemSetting': 'settingRecorded'}.get(kind)
            if form:
                result = bench.check('Q1', {form: [fid]})
                self.assertEqual(result['status'], 'verified', result)
        if not any(kind == 'systemSetting' for _, kind in kinds):
            self.assertEqual(bench.evidence_needs()['status'], 'diagnostic')
            collected = bench.collect('system', 'Computer A')
            self.assertEqual(collected['status'], 'completed', collected)
            bench.update_question('Q1', unresolved=['Inspect the new system records'], status='in_progress')
        return {'summary': 'Synthetic tool workflow', 'turns': 1, 'tool_calls': None,
                'seconds': 0, 'ended': 'success'}

    def invoke(self, arguments):
        with patch('app.cli._job_manager', side_effect=lambda root: InlineManager(root, self.backend)), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            code = cli.main(arguments, root=self.root)
        self.assertEqual(code, 0, output.getvalue())
        return output.getvalue()

    def test_images_to_report_automatically_continues_on_new_snapshot(self):
        output = self.invoke(['investigate', '--name', 'case', '--images', str(self.images),
            '--exhibits', str(self.manifest_file), '--readers', 'inventory', '--backend', 'deepagents',
            '--question', 'What records are available?', '--minutes', '1', '--follow-up-stages', '1'])
        first = self.root / 'runs/case'
        second = self.root / 'runs/case-followup'
        a, b = [json.loads((p / 'run.json').read_text()) for p in (first, second)]
        self.assertEqual(a['stats']['verified'], 1)
        self.assertEqual(b['stats']['verified'], 2)
        self.assertFalse(b['continuation']['same_evidence'])
        self.assertEqual(b['continuation_replay']['replayed'], [])
        self.assertNotEqual(a['case']['facts_sha256'], b['case']['facts_sha256'])
        self.assertEqual(a['case_answers']['questions'][0]['prompt'], b['case_answers']['questions'][0]['prompt'])
        self.assertIn('New evidence snapshot:', output)
        for saved in (a, b):
            self.assertEqual(saved['coverage']['inspection']['status'], 'measured')
            self.assertEqual(saved['coverage']['inspection']['audit_integrity'], 'passed')
            self.assertEqual(saved['coverage']['inspection']['record_count'], 0)
        for path in (first, second):
            self.assertTrue((path / 'report.html').is_file())
            self.assertTrue((path / 'case-answers.json').is_file())
        self.assertEqual(self.stages[1]['questions'][0]['finding_ids'], [])
        self.assertIn('Inspect the new system records', json.dumps(self.stages[1]))
        original = {p.name: p.read_bytes() for p in second.iterdir() if p.is_file()}
        self.invoke(['resume', '--run', str(second), '--name', 'follow-question',
                     '--question', 'Which settings remain unresolved?', '--minutes', '1'])
        continued = json.loads((self.root / 'runs/follow-question/run.json').read_text())
        self.assertEqual(len(continued['case_answers']['questions']), 2)
        self.assertEqual(continued['case_answers']['questions'][1]['status'], 'unanswered')
        self.assertEqual(original, {p.name: p.read_bytes() for p in second.iterdir() if p.is_file()})
