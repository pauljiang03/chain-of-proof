"""Independent native C failure paths; real proofs, no model or private key."""
import json
import unittest
from unittest.mock import patch

from checker import check as checker
from comparison.ablation import runtime
from tests import test_ablation_checkpoint_runtime as checkpoint_fixture


class NativeTrialFailurePaths(unittest.TestCase):
    setUp = checkpoint_fixture.Checkpoints.setUp
    init = checkpoint_fixture.Checkpoints.init
    document = checkpoint_fixture.Checkpoints.document
    binding = checkpoint_fixture.Checkpoints.binding

    def test_batch_stops_before_new_checker_call_after_deadline(self):
        run = self.init('C')
        session = json.loads((run / 'session.json').read_text())
        clock = {'now': session['deadline_unix'] - 1}
        calls = []
        original = checker.check

        def checked(*args, **kwargs):
            calls.append(clock['now'])
            result = original(*args, **kwargs)
            clock['now'] = session['deadline_unix'] + 1
            return result

        with runtime._bench(run) as (directory, session, bench), \
                patch.object(checker, 'check', side_effect=checked), \
                patch('comparison.ablation.checkpoints.time.time', side_effect=lambda: clock['now']):
            result = runtime._record_call(directory, bench, 'check', {'question': 'Q1', 'claims': [
                {'usbConnected': [1]}, {'exactly': ['usbInsert', 1]},
                {'both': [{'usbConnected': [1]}, {'usbConnected': [1]}]}]},
                protocol='claim-bindings-v3', session=session)
        self.assertEqual(len(calls), 1, 'Queued claims must not start a new checker after the deadline.')
        self.assertTrue(all(start < session['deadline_unix'] for start in calls))
        proposals = [json.loads(line) for line in (run / 'proposals.jsonl').read_text().splitlines()]
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0]['status'], 'verified')
        self.assertEqual(result[0]['status'], 'verified')
        for queued in result[1:]:
            self.assertEqual(queued['status'], 'time_limit')
            self.assertIs(queued['checked'], False)
            self.assertNotIn('candidate_id', queued)
            self.assertNotIn('finding_id', queued)
        self.assertEqual(len(result), 3)
        event = json.loads((run / 'bridge-calls.jsonl').read_text().splitlines()[-1])
        self.assertEqual([row['position'] for row in event['batch']], [1, 2, 3])
        self.assertEqual(event['result'], result)
        self.assertTrue(all(row['candidate_id'] is None and row['finding_id'] is None
                            for row in event['batch'][1:]))

    def test_check_at_exact_deadline_never_enters_the_checker(self):
        run = self.init('C')
        with runtime._bench(run) as (directory, session, bench), \
                patch.object(checker, 'check', wraps=checker.check) as actual, \
                patch('comparison.ablation.checkpoints.time.time', return_value=session['deadline_unix']):
            with self.assertRaises(ValueError):
                runtime._record_call(directory, bench, 'check', {'question': 'Q1', 'claim': {'usbConnected': [1]}},
                                     protocol='claim-bindings-v3', session=session)
            actual.assert_not_called()
        self.assertFalse((run / 'proposals.jsonl').exists())

    def test_c_timeout_preserves_selected_checkpoint_without_later_binding_inference(self):
        run = self.init('C')
        first = runtime.call_tool(run, 'check', {'question': 'Q1', 'claim': {'usbConnected': [1]}})
        self.assertEqual(first['status'], 'verified')
        document = self.document([self.binding(first['finding_id'])])
        runtime.call_tool(run, 'checkpoint', {'document': document})
        saved = (run / 'binding-checkpoint.json').read_bytes()
        # A later distinct proof is not permission to rewrite the saved document.
        later = runtime.call_tool(run, 'check', {'question': 'Q1', 'claim': {'exactly': ['usbInsert', 1]}})
        self.assertEqual(later['status'], 'verified')
        self.summary.write_text('No final binding JSON was returned.')
        trial = runtime.finalize_session(run, summary=self.summary, status='time_limit')
        self.assertEqual(trial['projection']['status'], 'available')
        self.assertTrue(trial['certificate_replay']['passed'])
        self.assertEqual((run / 'binding-checkpoint.json').read_bytes(), saved)
        self.assertEqual(json.loads((run / 'bindings.json').read_text()), document)
        projection = json.loads((run / 'projection.json').read_text())
        self.assertEqual(projection['submission']['answers'][0]['answer'], 'fixture-device')
        self.assertEqual({leaf['candidate_id'] for leaf in projection['leaves']}, {first['finding_id']})
        self.assertNotIn(later['finding_id'], projection['projection']['candidates'])

    def test_mutated_facts_before_finalization_cannot_publish_a_trial(self):
        run = self.init('C')
        first = runtime.call_tool(run, 'check', {'question': 'Q1', 'claim': {'usbConnected': [1]}})
        runtime.call_tool(run, 'checkpoint', {'document': self.document([self.binding(first['finding_id'])])})
        checkpoint_bytes = (run / 'binding-checkpoint.json').read_bytes()
        self.summary.write_text('Interrupted before final prose.')
        self.facts.write_bytes(self.facts.read_bytes() + b'\n')
        with self.assertRaises(ValueError):
            runtime.finalize_session(run, summary=self.summary, status='time_limit')
        self.assertFalse((run / 'trial.json').exists())
        self.assertEqual((run / 'binding-checkpoint.json').read_bytes(), checkpoint_bytes)

    def test_valid_final_json_cannot_replace_the_saved_c_checkpoint(self):
        run = self.init('C')
        first = runtime.call_tool(run, 'check', {'question': 'Q1', 'claim': {'usbConnected': [1]}})
        saved = self.document([self.binding(first['finding_id'])])
        runtime.call_tool(run, 'checkpoint', {'document': saved})
        invented = self.document([dict(self.binding(first['finding_id']), value='invented final value')])
        summary = ('Final prose.\n```json\n' + json.dumps(invented) + '\n```\n').encode()
        self.summary.write_bytes(summary)
        trial = runtime.finalize_session(run, summary=self.summary, status='completed')
        self.assertEqual(trial['projection']['status'], 'available')
        self.assertEqual((run / 'summary.md').read_bytes(), summary)
        self.assertEqual(json.loads((run / 'bindings.json').read_text()), saved)
        projected = json.loads((run / 'projected-answers.json').read_text())
        self.assertEqual(projected['answers'][0]['answer'], 'fixture-device')

    def test_tampered_online_certificate_cannot_publish_checkpoint_answers(self):
        run = self.init('C')
        first = runtime.call_tool(run, 'check', {'question': 'Q1', 'claim': {'usbConnected': [1]}})
        runtime.call_tool(run, 'checkpoint', {'document': self.document([self.binding(first['finding_id'])])})
        path = run / (first['finding_id'] + '.json')
        certificate = json.loads(path.read_text())
        certificate['english'] = 'This tampered statement was never certified.'
        path.write_text(json.dumps(certificate))
        self.summary.write_text('Saved checkpoint exists; independent replay must still pass.')
        trial = runtime.finalize_session(run, summary=self.summary, status='completed')
        self.assertFalse(trial['certificate_replay']['passed'])
        self.assertEqual(trial['status'], 'failed')
        self.assertEqual(trial['projection']['status'], 'unavailable')
        self.assertFalse((run / 'projected-answers.json').exists())


if __name__ == '__main__':
    unittest.main()
