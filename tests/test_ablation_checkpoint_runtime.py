"""Deterministic durable transport tests; no model calls."""
import json
import time
import unittest
from unittest.mock import patch
from tests import test_ablation_protocol_runtime as fixture
from comparison.ablation import runtime


class Checkpoints(unittest.TestCase):
    def setUp(self):
        fixture.ProtocolRuntime.setUp(self)
        from agent.answer_requirements import KEY
        self.public['questions'][0]['answer_schema'][KEY] = {
            'semantic_types': ['device_serial'], 'meaning': 'Device serial',
            'evidence_needed': 'Connection record'}
        self.questions.write_text(json.dumps(self.public))
    binding = fixture.ProtocolRuntime.binding

    def init(self, arm='A', name='run'):
        run = self.root / name
        runtime.init_session(arm=arm, facts=self.facts, case_profile=self.profile,
            questions=self.questions, out=run, protocol='claim-bindings-v3', deadline_unix=time.time()+300)
        return run

    def document(self, bindings=None):
        return {'schema_version': 1, 'case_id': 'fixture', 'bindings': bindings or [],
                'unanswered': [] if bindings else [{'question_id': 'Q1', 'reason': 'Still searching'}]}

    def test_unannotated_contract_refused_before_output_creation(self):
        from agent.answer_requirements import KEY
        del self.public['questions'][0]['answer_schema'][KEY]
        self.questions.write_text(json.dumps(self.public))
        with self.assertRaisesRegex(ValueError, 'missing_annotation'):
            self.init()
        self.assertFalse((self.root/'run').exists())

    def test_preflight_reports_supported_and_unknown_declared_roles(self):
        from comparison.ablation.checkpoints import public_preflight
        from agent.answer_requirements import KEY
        ready = public_preflight(self.public)
        self.assertEqual(ready['supported_fields'], 1)
        self.public['questions'][0]['answer_schema'][KEY]['semantic_types'] = ['no_such_role']
        ready = public_preflight(self.public)
        self.assertEqual(ready['unsupported_fields'], 1)
        self.assertEqual(ready['evidence_needs'][0]['status'], 'no_catalog_support')

    def test_timeout_uses_checkpoint_not_final_prose_and_seals(self):
        run = self.init()
        document = self.document()
        runtime.call_tool(run, 'checkpoint', {'document': document})
        self.summary.write_text('No final binding document')
        with patch('comparison.ablation.checkpoints.time.time', return_value=time.time()+600):
            trial = runtime.finalize_session(run, summary=self.summary, status='time_limit')
        self.assertEqual(trial['projection']['status'], 'available')
        self.assertEqual(json.loads((run/'bindings.json').read_text()), document)
        with self.assertRaises(ValueError):
            runtime.call_tool(run, 'checkpoint', {'document': document})

    def test_timeout_preserves_valid_partial_binding_and_wrong_literal(self):
        from agent.answer_requirements import KEY
        requirement = {'semantic_types': ['device_serial'], 'meaning': 'Recorded device',
                       'evidence_needed': 'Device connection record'}
        self.public['questions'][0]['answer_schema'] = {'type': 'object', 'properties': {
            'serial': {'type': 'string', KEY: requirement},
            'unknown': {'type': 'string', KEY: requirement}}}
        self.questions.write_text(json.dumps(self.public))
        run = self.init()
        cid = runtime.call_tool(run, 'check', {'question': 'Q1', 'claim': {'usbConnected': [1]}})['candidate_id']
        document = self.document([dict(self.binding(cid), path=['serial'])])
        runtime.call_tool(run, 'checkpoint', {'document': document})
        self.summary.write_text('Timeout')
        trial = runtime.finalize_session(run, summary=self.summary, status='time_limit')
        self.assertEqual(trial['projection']['status'], 'available')
        answer = json.loads((run/'projected-answers.json').read_text())['answers'][0]['answer']
        self.assertEqual(answer, {'serial': 'fixture-device'})

    def test_invalid_or_late_update_preserves_bytes(self):
        run = self.init()
        runtime.call_tool(run, 'checkpoint', {'document': self.document()})
        before = (run/'binding-checkpoint.json').read_bytes()
        with self.assertRaises(ValueError):
            runtime.call_tool(run, 'checkpoint', {'document': self.document([{}])})
        with patch('comparison.ablation.checkpoints.time.time', return_value=time.time()+600):
            with self.assertRaises(ValueError):
                runtime.call_tool(run, 'checkpoint', {'document': self.document()})
        self.assertEqual((run/'binding-checkpoint.json').read_bytes(), before)

    def test_post_validation_deadline_preserves_bytes(self):
        run = self.init()
        runtime.call_tool(run, 'checkpoint', {'document': self.document()})
        before = (run/'binding-checkpoint.json').read_bytes()
        from comparison.ablation import checkpoints
        with patch.object(checkpoints, 'deadline', side_effect=[None, None, ValueError('late')]):
            with self.assertRaises(ValueError):
                runtime.call_tool(run, 'checkpoint', {'document': self.document()})
        self.assertEqual((run/'binding-checkpoint.json').read_bytes(), before)

    def test_deadline_crossing_replace_rolls_back_exact_prior(self):
        from comparison.ablation import checkpoints
        run = self.init()
        runtime.call_tool(run, 'checkpoint', {'document': self.document()})
        before = (run/'binding-checkpoint.json').read_bytes()
        with patch.object(checkpoints, 'deadline', side_effect=[None, None, None, ValueError('late commit')]):
            with self.assertRaises(ValueError):
                runtime.call_tool(run, 'checkpoint', {'document': self.document()})
        self.assertEqual((run/'binding-checkpoint.json').read_bytes(), before)

    def test_persistent_bridge_validates_inputs_once(self):
        import io
        run = self.init()
        requests = io.StringIO(''.join(json.dumps({'tool': 'preview', 'arguments': {'document': self.document()}})+'\n' for _ in range(2)))
        with patch.object(runtime, '_session', wraps=runtime._session) as session:
            runtime.serve_session(run, stdin=requests, stdout=io.StringIO())
        self.assertEqual(session.call_count, 1)

    def test_no_checkpoint_unavailable_even_valid_final_document(self):
        run = self.init()
        self.summary.write_text('```json\n'+json.dumps(self.document())+'\n```\n')
        trial = runtime.finalize_session(run, summary=self.summary, status='completed')
        self.assertEqual(trial['projection']['status'], 'unavailable')

    def test_preview_parity_no_checker_or_repair(self):
        a, c = self.init(name='A'), self.init('C', 'C')
        claim = {'usbConnected': [1]}
        candidate = {'schema_version': 1, 'sequence': 1, 'candidate_id': 'P000001', 'question': 'Q1', 'claim': claim}
        (a/'candidates.jsonl').write_text(json.dumps(candidate)+'\n')
        (c/'proposals.jsonl').write_text(json.dumps(candidate)+'\n')
        document = self.document([self.binding('P000001', claim_sha256='0'*64, value='wrong')])
        with patch('checker.check.check', side_effect=AssertionError('checker')), patch('checker.claims.parse', side_effect=AssertionError('parse')):
            left = runtime.call_tool(a, 'preview', {'document': document})
            right = runtime.call_tool(c, 'preview', {'document': document})
        self.assertEqual(left, right)
        self.assertEqual(left['status'], 'uncertified')
        self.assertGreater(left['diagnostic_count'], 0)
        runtime.call_tool(a, 'checkpoint', {'document': document})
        self.assertEqual(json.loads((a/'binding-checkpoint.json').read_text())['document'], document)

    def test_c_checkpoint_timeout_independently_replays_exact_certificate(self):
        run = self.init('C')
        receipt = runtime.call_tool(run, 'check', {'question': 'Q1', 'claim': {'usbConnected': [1]}})
        self.assertEqual(receipt['status'], 'verified')
        document = self.document([self.binding(receipt['finding_id'])])
        runtime.call_tool(run, 'checkpoint', {'document': document})
        checkpoint_bytes = (run/'binding-checkpoint.json').read_bytes()
        self.summary.write_text('Investigator stopped without final JSON.')
        from verifier.verify import verify_run
        with patch('verifier.verify.verify_run', wraps=verify_run) as replay, patch(
                'comparison.ablation.checkpoints.time.time', return_value=time.time()+600):
            trial = runtime.finalize_session(run, summary=self.summary, status='time_limit')
        self.assertEqual(replay.call_count, 1)
        self.assertTrue(trial['certificate_replay']['passed'])
        self.assertEqual(trial['certificate_replay']['checked'], 1)
        self.assertEqual(trial['certificate_replay']['verified'], 1)
        self.assertEqual(trial['projection']['status'], 'available')
        self.assertEqual((run/'binding-checkpoint.json').read_bytes(), checkpoint_bytes)
        self.assertEqual(json.loads((run/'bindings.json').read_text()), document)
        answer = json.loads((run/'projected-answers.json').read_text())['answers'][0]
        self.assertEqual(answer['answer'], 'fixture-device')

    def test_predicted_future_candidate_never_gains_checkpoint_support(self):
        run = self.init()
        document = self.document([self.binding('P000001')])
        runtime.call_tool(run, 'checkpoint', {'document': document})
        checkpoint_bytes = (run/'binding-checkpoint.json').read_bytes()
        candidate = runtime.call_tool(run, 'check', {'question': 'Q1', 'claim': {'usbConnected': [1]}})
        self.assertEqual(candidate['candidate_id'], 'P000001')
        self.summary.write_text('Stopped')
        trial = runtime.finalize_session(run, summary=self.summary, status='time_limit')
        self.assertEqual(trial['projection']['status'], 'available')
        self.assertEqual((run/'binding-checkpoint.json').read_bytes(), checkpoint_bytes)
        projection = json.loads((run/'projection.json').read_text())
        self.assertEqual(projection['submission']['answers'][0]['status'], 'unknown')
        self.assertEqual(projection['projection']['candidates'], {})
        self.assertTrue(projection['unsupported'])
        self.assertEqual(json.loads((run/'binding-resolution.json').read_text()), [])

    def test_candidate_prefix_tamper_fails_closed(self):
        run = self.init()
        cid = runtime.call_tool(run, 'check', {'question': 'Q1', 'claim': {'usbConnected': [1]}})['candidate_id']
        runtime.call_tool(run, 'checkpoint', {'document': self.document([self.binding(cid)])})
        path = run/'candidates.jsonl'
        path.write_bytes(path.read_bytes().replace(b'usbConnected', b'fileRecorded'))
        self.summary.write_text('Stopped')
        trial = runtime.finalize_session(run, summary=self.summary, status='time_limit')
        self.assertEqual(trial['projection']['status'], 'unavailable')


if __name__ == '__main__':
    unittest.main()
