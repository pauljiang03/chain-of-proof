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
            try:
                runtime._record_call(directory, bench, 'check', {'question': 'Q1', 'claims': [
                    {'usbConnected': [1]}, {'exactly': ['usbInsert', 1]}]},
                    protocol='claim-bindings-v3', session=session)
            except (ValueError, TimeoutError):
                pass  # A failed batch may retain the completed first certificate.
        self.assertEqual(len(calls), 1, 'Queued claims must not start a new checker after the deadline.')
        self.assertTrue(all(start < session['deadline_unix'] for start in calls))
        proposals = [json.loads(line) for line in (run / 'proposals.jsonl').read_text().splitlines()]
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0]['status'], 'verified')

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


if __name__ == '__main__':
    unittest.main()
