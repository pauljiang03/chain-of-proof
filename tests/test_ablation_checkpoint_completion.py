"""Saved investigator documents, not later candidates, drive neutral completion."""
import json
import unittest
from unittest.mock import patch
from comparison.ablation import runtime
from tests import test_ablation_checkpoint_runtime as fixture


class CheckpointCompletion(unittest.TestCase):
    setUp = fixture.Checkpoints.setUp
    init = fixture.Checkpoints.init
    document = fixture.Checkpoints.document
    binding = fixture.Checkpoints.binding

    def test_missing_checkpoint_plan_does_not_infer_answer(self):
        run = self.init()
        runtime.call_tool(run, 'check', {'question': 'Q1', 'claim': {'usbConnected': [1]}})
        completion = runtime.call_tool(run, 'plan', {})['completion']
        self.assertEqual(completion['status'], 'unavailable')
        self.assertFalse(completion['answers_inferred'])
        self.assertEqual(completion['counts']['current_candidates'], 1)
        self.assertNotIn('unknown_questions', completion['counts'])
        self.assertNotIn('submission', completion)

    def test_checkpoint_lag_does_not_resolve_future_candidate(self):
        run = self.init()
        receipt = runtime.call_tool(run, 'checkpoint', {'document': self.document([self.binding('P000001')])})
        self.assertEqual(receipt['completion']['counts']['surviving_leaves'], 0)
        runtime.call_tool(run, 'check', {'question': 'Q1', 'claim': {'usbConnected': [1]}})
        completion = runtime.call_tool(run, 'plan', {})['completion']
        self.assertEqual(completion['checkpoint']['candidates_since_checkpoint'], 1)
        self.assertEqual(completion['counts']['surviving_leaves'], 0)
        self.assertEqual(completion['counts']['unknown_questions'], 1)

    def test_checkpoint_replacement_cannot_pair_old_document_with_new_population(self):
        from comparison.ablation import checkpoints
        run = self.init()
        runtime.call_tool(run, 'checkpoint', {'document': self.document([self.binding('P000001')])})
        old = (run/checkpoints.FILE).read_bytes()
        runtime.call_tool(run, 'check', {'question': 'Q1', 'claim': {'usbConnected': [1]}})
        runtime.call_tool(run, 'checkpoint', {'document': self.document()})
        newer = (run/checkpoints.FILE).read_bytes()
        (run/checkpoints.FILE).write_bytes(old)
        original_read = runtime._read
        reads = []
        def replacing_read(path):
            raw = original_read(path)
            if path.name == checkpoints.FILE:
                reads.append(raw)
                if len(reads) == 1:
                    (run/checkpoints.FILE).write_bytes(newer)
            return raw
        with patch.object(runtime, '_read', side_effect=replacing_read):
            completion = runtime.call_tool(run, 'plan', {})['completion']
        self.assertEqual(len(reads), 1)
        self.assertEqual(completion['counts']['authored_bindings'], 1)
        self.assertEqual(completion['checkpoint']['saved_candidates'], 0)
        self.assertEqual(completion['counts']['surviving_leaves'], 0)
        self.assertEqual(completion['counts']['unknown_questions'], 1)

    def test_removed_bindings_warn_but_intentional_document_replaces(self):
        run = self.init()
        cid = runtime.call_tool(run, 'check', {'question': 'Q1', 'claim': {'usbConnected': [1]}})['candidate_id']
        runtime.call_tool(run, 'checkpoint', {'document': self.document([self.binding(cid)])})
        new = self.document()
        receipt = runtime.call_tool(run, 'checkpoint', {'document': new})
        self.assertEqual(receipt['removed_authored_bindings'], 1)
        self.assertEqual(receipt['completion']['counts']['surviving_leaves'], 0)
        self.assertEqual(json.loads((run/'binding-checkpoint.json').read_text())['document'], new)

    def test_preview_and_plan_are_neutral_ac_and_retain_inventory_gap(self):
        a, c = self.init(name='A'), self.init('C', 'C')
        for run in (a, c):
            runtime.call_tool(run, 'inventory_page', {'question_id': 'Q1', 'page_size': 1})
            runtime.call_tool(run, 'checkpoint', {'document': self.document()})
        with patch('checker.check.check', side_effect=AssertionError('checker feedback')):
            left = runtime.call_tool(a, 'preview', {'document': self.document()})
            right = runtime.call_tool(c, 'preview', {'document': self.document()})
        self.assertEqual(left, right)
        self.assertEqual(left['completion']['counts']['returned_rows_with_zero_authored_bindings'], 1)
        self.assertEqual(left['completion']['counts']['unknown_questions'], 1)
        self.assertNotIn('fixture-device', json.dumps(left))

    def test_large_inventory_preserves_all_authored_values_with_bounded_receipt(self):
        count = 1500
        facts = json.loads(self.facts.read_text())
        facts['strings'].update({str(1000+i): 'SERIAL-'+str(i) for i in range(count)})
        prototype = facts['facts'][0]
        facts['facts'] = [dict(prototype, id=i+1, obj=1000+i) for i in range(count)]
        self.facts.write_text(json.dumps(facts))
        leaf = self.public['questions'][0]['answer_schema']
        self.public['questions'][0]['answer_schema'] = {'type': 'array', 'items': leaf}
        self.questions.write_text(json.dumps(self.public))
        run = self.init()
        candidates, bindings = [], []
        for index in range(count):
            cid = 'P'+str(index+1).zfill(6)
            candidates.append({'schema_version': 1, 'sequence': index+1, 'candidate_id': cid,
                               'question': 'Q1', 'claim': {'usbConnected': [index+1]}})
            bindings.append(dict(self.binding(cid), path=[index]))
        (run/'candidates.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in candidates))
        receipt = runtime.call_tool(run, 'checkpoint', {'document': self.document(bindings)})
        self.assertEqual(receipt['completion']['counts']['surviving_leaves'], count)
        self.assertNotIn('SERIAL-', json.dumps(receipt))
        self.assertLess(len(json.dumps(receipt)), 10000)
        self.assertEqual(len(json.loads((run/'binding-checkpoint.json').read_text())['document']['bindings']), count)
        self.summary.write_text('Timeout')
        runtime.finalize_session(run, summary=self.summary, status='time_limit')
        answer = json.loads((run/'projected-answers.json').read_text())['answers'][0]['answer']
        self.assertEqual(answer, ['SERIAL-'+str(i) for i in range(count)])

    def test_timeout_retains_value_free_artifact_for_valid_checkpoint(self):
        run = self.init()
        cid = runtime.call_tool(run, 'check', {'question': 'Q1', 'claim': {'usbConnected': [1]}})['candidate_id']
        runtime.call_tool(run, 'checkpoint', {'document': self.document([self.binding(cid)])})
        self.summary.write_text('Timeout without final document')
        trial = runtime.finalize_session(run, summary=self.summary, status='time_limit')
        self.assertEqual(trial['completion']['status'], 'uncertified')
        artifact = json.loads((run/'completion-diagnostics.json').read_text())
        self.assertEqual(artifact['counts']['surviving_leaves'], 1)
        self.assertNotIn('fixture-device', json.dumps(artifact))

    def test_artifact_survives_later_finalizer_failure_without_masking_it(self):
        run = self.init('C')
        runtime.call_tool(run, 'checkpoint', {'document': self.document()})
        self.summary.write_text('Timeout')
        with patch('checker.export.bundle', side_effect=ValueError('original replay failure')):
            with self.assertRaisesRegex(ValueError, 'original replay failure'):
                runtime.finalize_session(run, summary=self.summary, status='time_limit')
        artifact = json.loads((run/'completion-diagnostics.json').read_text())
        self.assertEqual(artifact['counts']['unknown_questions'], 1)
        self.assertTrue((run/'.finalizing').exists())

    def test_timeout_artifact_and_stale_prefix_refusal(self):
        run = self.init()
        cid = runtime.call_tool(run, 'check', {'question': 'Q1', 'claim': {'usbConnected': [1]}})['candidate_id']
        runtime.call_tool(run, 'checkpoint', {'document': self.document([self.binding(cid)])})
        path = run/'candidates.jsonl'
        path.write_bytes(path.read_bytes().replace(b'usbConnected', b'fileRecorded'))
        self.assertEqual(runtime.call_tool(run, 'plan', {})['completion']['status'], 'unavailable')
        self.summary.write_text('Timeout')
        trial = runtime.finalize_session(run, summary=self.summary, status='time_limit')
        self.assertEqual(trial['projection']['status'], 'unavailable')
        artifact = json.loads((run/'completion-diagnostics.json').read_text())
        self.assertEqual(artifact['status'], 'unavailable')
        self.assertFalse(artifact['answers_inferred'])


if __name__ == '__main__':
    unittest.main()
