"""Offline job lifecycle and bounded artifact views; no provider is contacted."""
import contextlib
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest.mock import patch

from app import jobs

ROOT = Path(__file__).resolve().parent.parent
FACTS = ROOT / 'fixtures/sample_facts.json'
REAL_POPEN = subprocess.Popen


def wait_for(predicate, timeout=12):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        value = predicate()
        if value:
            return value
        time.sleep(.03)
    raise AssertionError('Timed out waiting for the synthetic job.')


def alive(pid):
    row = jobs._processes().get(pid)
    if row is None:
        return False
    result = subprocess.run(['ps', '-o', 'stat=', '-p', str(pid)], capture_output=True, text=True)
    return bool(result.stdout.strip()) and not result.stdout.strip().startswith('Z')


class JobTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manager = jobs.JobManager(self.root)
        self.addCleanup(self.manager.close)
        self.binary = self.root / 'bin'
        self.binary.mkdir()
        self.env = patch.dict(os.environ, {'PATH': str(self.binary) + os.pathsep + os.environ['PATH']})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.fake_cli("print('{\"type\":\"result\",\"subtype\":\"success\",\"result\":\"Synthetic summary\"}')")

    def fake_cli(self, program):
        executable = self.binary / 'claude'
        executable.write_text('#!' + sys.executable + '\n' + program + '\n')
        executable.chmod(0o700)

    def start(self, name='trial', **extra):
        return self.manager.start({'name': name, 'facts': str(FACTS), **extra})

    def terminal(self, name='trial'):
        wait_for(lambda: self.manager._jobs[name]['done'].is_set())
        return self.manager.get_run(name)

    def saved(self, name='saved', case=None):
        directory = self.root / 'runs' / name
        directory.mkdir(parents=True)
        jobs._write_json(directory / 'run.json', {'schema_version': 2,
            'case': {'name': 'Public case', **(case or {})},
            'stats': {'verified': 0, 'rejected': 0}, 'findings': []})
        return directory

    def test_defaults_and_backend_aware_model(self):
        config = self.manager.config()
        self.assertEqual(config['defaults']['backend'], 'claude-code')
        self.assertEqual(config['defaults']['minutes'], 45)
        self.assertIsNone(config['active_run'])
        self.assertTrue(config['backends'][0]['available'])
        prepared = self.manager._prepare({'name': 'a', 'facts': str(FACTS), 'backend': 'deepagents',
                                         'title': '', 'brief': ''}, None, None)
        self.assertEqual(prepared['model'], 'claude-opus-5-5')
        self.assertTrue(prepared['profile']['questions'])
        self.assertNotIn('API_KEY', json.dumps(config))

    def test_invalid_public_inputs_never_spawn(self):
        for changes in ({'name': '../escape'}, {'name': 'sample'}, {'name': 'gate-probes/a'},
                        {'reference': 'private.json'}, {'minutes': True}, {'minutes': 0},
                        {'questions': ['']}, {'questions': [2]}, {'questions': 'question'},
                        {'backend': 'shell'}, {'model': 22}, {'brief': None}, {'facts': '/missing.json'}):
            with self.subTest(changes=changes), patch.object(self.manager, '_spawn') as spawn:
                with self.assertRaises(ValueError):
                    self.manager.start({'name': 'a', 'facts': str(FACTS), **changes})
                spawn.assert_not_called()
        profile = self.root / 'private.json'
        profile.write_text(json.dumps({'name': 'Case', 'brief': 'Public', 'questions': ['Question'],
                                       'reference': 'SECRET'}))
        with patch.object(self.manager, '_spawn') as spawn, self.assertRaises(ValueError):
            self.manager.start({'name': 'a', 'facts': str(FACTS)}, case_profile=profile)
        spawn.assert_not_called()

    def test_raw_disk_and_malformed_fact_store_rejected(self):
        for filename, text in [('image.E01', '{}'), ('bad.json', '{"facts":[{}]}')]:
            path = self.root / filename
            path.write_text(text)
            with self.assertRaises(ValueError):
                self.start(facts=str(path))

    def test_success_uses_actual_runner_and_outputs_report(self):
        self.assertEqual(self.start(), {'name': 'trial', 'status': 'running'})
        snapshot = self.terminal()
        self.assertEqual(snapshot['status'], 'completed')
        self.assertEqual(snapshot['run']['case']['ended'], 'success')
        directory = self.root / 'runs/trial'
        self.assertTrue((directory / 'report.md').is_file())
        self.assertFalse(json.loads((directory / 'results.json').read_text())['evaluation']['measured'])
        self.assertIsNone(self.manager.config()['active_run'])
        with self.assertRaises(FileExistsError):
            self.start()

    def test_nonzero_cli_exit_stays_failed_and_hides_output(self):
        self.fake_cli("import sys\nprint('SECRET_PROVIDER', file=sys.stderr)\n"
                      "print('{\"type\":\"result\",\"subtype\":\"success\",\"result\":\"partial\"}')\n"
                      "raise SystemExit(3)")
        self.start()
        snapshot = self.terminal()
        self.assertEqual(snapshot['status'], 'failed')
        self.assertEqual(snapshot['run']['case']['exit_code'], 3)
        self.assertNotIn('SECRET_PROVIDER', json.dumps(snapshot))
        self.assertTrue((self.root / 'runs/trial/report.md').exists())

    def test_one_active_close_and_real_detached_child_cleanup(self):
        pids = self.root / 'pids.json'
        grandchild = 'import time; time.sleep(120)'
        self.fake_cli('import os, subprocess, sys, time, json\n'
                      f'child = subprocess.Popen([sys.executable, "-c", {grandchild!r}], start_new_session=True)\n'
                      f'open({str(pids)!r}, "w").write(json.dumps([os.getpid(), child.pid]))\n'
                      'time.sleep(120)')
        self.start()
        wait_for(pids.exists)
        selected = json.loads(pids.read_text())
        self.assertIn(selected[0], jobs._processes(), "Lifecycle tests require ps access.")
        self.addCleanup(self.kill_fixture, selected)
        with self.assertRaises(RuntimeError):
            self.start('other')
        self.manager.close()
        self.assertEqual(self.terminal()['status'], 'cancelled')
        for pid in selected:
            wait_for(lambda pid=pid: not alive(pid), timeout=3)
        self.assertTrue((self.root / 'runs/trial/report.md').exists())
        with self.assertRaises(RuntimeError):
            self.start('after-close')

    @staticmethod
    def kill_fixture(pids):
        for pid in pids:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    def test_bounded_fallback_kills_ignoring_worker_and_detached_child(self):
        pidfile = self.root / 'fallback-pids.json'
        def spawn(command, env):
            specpath = command[command.index('--spec') + 1]
            script = '''import json, os, pathlib, signal, subprocess, sys, time
spec=json.loads(pathlib.Path(sys.argv[1]).read_text())
root=pathlib.Path(sys.argv[2]); directory=root/'runs'/spec['name']; directory.mkdir(parents=True)
(directory/'app-job.json').write_text(json.dumps({'job_id':spec['job_id']}))
signal.signal(signal.SIGTERM, signal.SIG_IGN)
child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(120)'],start_new_session=True)
pathlib.Path(sys.argv[3]).write_text(json.dumps([os.getpid(), child.pid]))
time.sleep(120)
'''
            return REAL_POPEN([sys.executable, '-c', script, specpath, str(self.root), str(pidfile)],
                              env=env, start_new_session=True)
        with patch.object(self.manager, '_spawn', side_effect=spawn), patch.object(jobs, 'GRACE_SECONDS', .1):
            self.start()
            wait_for(pidfile.exists)
            selected = json.loads(pidfile.read_text())
            self.assertIn(selected[0], jobs._processes(), "Lifecycle tests require ps access.")
            self.addCleanup(self.kill_fixture, selected)
            self.assertEqual(self.manager.stop('trial')['status'], 'cancelled')
        for pid in selected:
            wait_for(lambda pid=pid: not alive(pid), timeout=3)
        self.assertIsNotNone(self.manager.get_run('trial')['run'])

    def test_finished_process_during_stop_keeps_completed_status(self):
        gate = threading.Event()
        original = self.manager._watch
        def delayed(name, job):
            job['process'].wait()
            gate.wait(10)
            original(name, job)
        with patch.object(self.manager, '_watch', side_effect=delayed):
            self.start()
            job = self.manager._jobs['trial']
            wait_for(lambda: job['process'].poll() is not None)
            timer = threading.Timer(.1, gate.set)
            timer.start()
            with patch.object(jobs, '_terminate') as terminate:
                self.assertEqual(self.manager.stop('trial')['status'], 'completed')
                terminate.assert_not_called()
            timer.join()
            self.assertFalse(job['cancel_requested'])

    def test_partial_recovery_preserves_truncated_bundle_and_certificate(self):
        directory = self.saved('partial')
        original = '{"case":'
        (directory / 'run.json').write_text(original)
        for suffix in ('json', 'lean'):
            (directory / ('N1.' + suffix)).write_bytes((ROOT / ('fixtures/sample_cert/N1.' + suffix)).read_bytes())
        jobs._write_json(directory / 'app-job.json', {'job_id': 'owned'})
        spec = {'job_id': 'owned', 'title': 'Partial', 'backend': 'claude-code', 'model': 'opus'}
        self.assertTrue(jobs._needs_report(directory))
        self.assertTrue(jobs._finish_partial(directory, spec, 'cancelled'))
        self.assertEqual((directory / 'interrupted-run.json').read_text(), original)
        self.assertEqual(len(jobs._read_json(directory / 'run.json')['findings']), 1)
        self.assertEqual(self.manager.get_run('partial')['status'], 'cancelled')
        self.assertTrue((directory / 'report.md').exists())

    def test_missing_report_rebuilt_but_unowned_artifacts_untouched(self):
        directory = self.saved()
        before = (directory / 'run.json').read_bytes()
        spec = {'job_id': 'different', 'title': 'Partial', 'backend': 'claude-code', 'model': 'opus'}
        self.assertFalse(jobs._finish_partial(directory, spec, 'cancelled'))
        self.assertEqual((directory / 'run.json').read_bytes(), before)
        self.assertTrue(jobs._needs_report(directory))
        jobs._write_json(directory / 'app-job.json', {'job_id': 'different'})
        self.assertTrue(jobs._finish_partial(directory, spec, 'failed'))
        self.assertTrue((directory / 'report.md').exists())

    def test_saved_status_truthful_for_legacy_errors_and_time_limit(self):
        cases = [({}, 'saved'), ({'exit_code': 0}, 'saved'), ({'exit_code': 1}, 'failed'),
                 ({'ended': 'success', 'exit_code': 0}, 'completed'),
                 ({'ended': 'time_limit', 'exit_code': -9}, 'partial'),
                 ({'ended': 'cancelled'}, 'cancelled')]
        for index, (case, expected) in enumerate(cases):
            name = 'run' + str(index)
            self.saved(name, case)
            self.assertEqual(self.manager.get_run(name)['status'], expected)

    def test_bad_saved_json_is_safe_failed_and_fifo_never_blocks(self):
        for index, value in enumerate(['[]', '{"case":[]}', '{"case":{},"stats":{},"findings":[],"x":NaN}',
                                      '{"case":{},"case":{},"stats":{},"findings":[]}']):
            directory = self.saved('bad' + str(index))
            (directory / 'run.json').write_text(value)
            snapshot = self.manager.get_run('bad' + str(index))
            self.assertIsNone(snapshot['run'])
            self.assertEqual(snapshot['status'], 'failed')
        directory = self.saved('fifo')
        (directory / 'run.json').unlink()
        os.mkfifo(directory / 'run.json')
        self.assertEqual(self.manager.get_run('fifo')['status'], 'failed')
        os.mkfifo(directory / 'audit.jsonl')
        self.assertEqual(self.manager.get_run('fifo')['events'], [])

    def test_listing_only_fixed_run_files_excludes_internal_and_symlinks(self):
        self.saved('public')
        for name in ('probes/check', 'gate-probes/negative', '.hidden'):
            self.saved(name)
        unrelated = self.root / 'runs/unrelated'
        unrelated.mkdir()
        (unrelated / 'secret.json').write_text('{}')
        (self.root / 'runs/link').symlink_to(self.root / 'runs/public', target_is_directory=True)
        with patch.object(jobs, 'SAMPLE', self.root / 'no-sample'):
            self.assertEqual([run['name'] for run in self.manager.list_runs()], ['public'])
        with self.assertRaises(ValueError):
            self.manager.get_run('link')
        with self.assertRaises(FileNotFoundError):
            self.manager.get_run('unrelated')
        with self.assertRaises(RuntimeError):
            self.manager.stop('public')

    def test_events_completed_bounded_allowlisted_and_strict_json(self):
        directory = self.saved()
        def event(n):
            return {'sequence': n, 'tool': 'fact', 'outcome': 'success',
                    'completed_at': '2026-11-14T00:00:00+00:00', 'finding_id': None,
                    'arguments': {'fact_id': n, 'private_reference': 'SECRET'},
                    'result': {'SECRET': 'transcript'}, 'error': 'SECRET'}
        path = directory / 'audit.jsonl'
        path.write_text('x' * (1024 * 1024 + 10) + '\n' +
                        ''.join(json.dumps(event(n)) + '\n' for n in range(1, 111)) +
                        '{"tool":"fact"}\n' + json.dumps(event(111)).replace('111', 'NaN') + '\n' +
                        json.dumps(event(112)) + '\n' + json.dumps(event(113)))
        result = self.manager.get_run('saved')['events']
        self.assertLessEqual(len(result), 100)
        self.assertEqual(result[-1]['sequence'], 112)
        self.assertNotIn('SECRET', json.dumps(result))
        self.assertEqual(set(result[-1]), set(jobs.EVENT_FIELDS))
        self.assertEqual(result[-1]['arguments'], {'fact_id': 112})
        path.write_text('{"tool":"fact", "arguments":{"fact_id":1}}')
        self.assertEqual(self.manager.get_run('saved')['events'], [])

    def test_reports_and_sample_are_read_only(self):
        directory = self.saved()
        original = (directory / 'run.json').read_bytes()
        with patch.object(jobs, 'SAMPLE', directory):
            self.assertEqual(self.manager.get_run('sample')['run']['case']['name'], 'Public case')
            self.assertTrue(next(row for row in self.manager.list_runs() if row['name'] == 'sample')['sample'])
        for fmt in ('md', 'json'):
            value, content_type, filename = self.manager.report('saved', fmt)
            self.assertTrue(value)
            self.assertTrue(content_type)
            self.assertEqual(filename, 'cop-saved.' + fmt)
        renderer = types.ModuleType('app.report')
        renderer.render_html = lambda run: '<html>Public</html>'
        with patch.dict(sys.modules, {'app.report': renderer}):
            self.assertEqual(self.manager.report('saved', 'html')[0], b'<html>Public</html>')
        self.assertEqual((directory / 'run.json').read_bytes(), original)
        with self.assertRaises(ValueError):
            self.manager.report('saved', '../secret')

    def test_worker_guard_registers_child_and_blocks_new_work_after_term(self):
        from agent import run
        stage = self.root / 'stage'
        stage.mkdir()
        spec = {'name': 'guard', 'facts': str(FACTS), 'title': 'Guard', 'backend': 'claude-code',
                'model': 'opus', 'minutes': 1, 'job_id': 'guard-id', 'case_profile': str(stage / 'profile.json')}
        jobs._write_json(stage / 'spec.json', spec)
        observed = []
        def fake_main(_args):
            run.prepare_run_dir('guard', run.ROOT)
            child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'], start_new_session=True)
            observed.append(child.pid)
            try:
                os.kill(os.getpid(), signal.SIGTERM)
            except KeyboardInterrupt:
                with self.assertRaises(KeyboardInterrupt):
                    subprocess.Popen([sys.executable, '-c', 'pass'])
                raise
        with patch.object(run, 'main', side_effect=fake_main), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(jobs._worker(self.root, stage / 'spec.json'), 1)
        self.assertTrue(observed)
        self.assertFalse(alive(observed[0]))
        self.assertEqual(jobs._read_json(stage / 'outcome.json')['status'], 'cancelled')
        self.assertIn(str(observed[0]), jobs._read_json(stage / 'children.json')['children'])
        self.assertIs(subprocess.Popen, REAL_POPEN)


    def test_term_inside_spawn_is_deferred_until_child_registration(self):
        from agent import run
        stage = self.root / 'spawn-stage'
        stage.mkdir()
        spec = {'name': 'spawn-race', 'facts': str(FACTS), 'title': 'Race', 'backend': 'claude-code',
                'model': 'opus', 'minutes': 1, 'job_id': 'race-id', 'case_profile': str(stage / 'profile.json')}
        jobs._write_json(stage / 'spec.json', spec)
        observed = []
        def interrupting_popen(*args, **kwargs):
            child = REAL_POPEN(*args, **kwargs)
            if args[0][0] == sys.executable:
                observed.append(child.pid)
                os.kill(os.getpid(), signal.SIGTERM)
            return child
        def fake_main(_args):
            run.prepare_run_dir('spawn-race', run.ROOT)
            subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'], start_new_session=True)
            self.fail('Cancellation should be raised after registration.')
        with patch.object(subprocess, 'Popen', side_effect=interrupting_popen), patch.object(run, 'main', side_effect=fake_main):
            self.assertEqual(jobs._worker(self.root, stage / 'spec.json'), 1)
        self.assertEqual(len(observed), 1)
        self.assertIn(str(observed[0]), jobs._read_json(stage / 'children.json')['children'])
        self.assertFalse(alive(observed[0]))
        self.assertEqual(jobs._read_json(stage / 'outcome.json')['status'], 'cancelled')


if __name__ == '__main__':
    unittest.main()
