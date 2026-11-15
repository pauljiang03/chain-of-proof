"""Offline protocol parity, neutral work state and exact final binding projection."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from agent.answer_projection import claim_digest
from comparison.ablation import runtime
from comparison.ablation.mcp_server import BINDING_TOOLS, TOOLS, tools_for


class ProtocolRuntime(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.facts = self.root / 'facts.json'
        self.facts.write_text(json.dumps({'strings': {'1': 'fixture-device', '2': 'fixture-volume'},
            'facts': [{'id': 1, 'kind': 'usbInsert', 't': 0, 'res': 0, 'obj': 1, 'aux': 2,
                       'prov': {'artifact': 'fixture'}}]}))
        self.profile = self.root / 'profile.json'
        self.profile.write_text(json.dumps({'name': 'fixture', 'brief': 'Public fixture investigation.',
            'questions': ['Which device?'], 'case_id': 'fixture'}))
        self.public = {'schema_version': 2, 'case_id': 'fixture', 'questions': [
            {'id': 'Q1', 'prompt': 'Which device?', 'answer_schema': {'type': 'string'}}]}
        self.questions = self.root / 'questions.json'
        self.questions.write_text(json.dumps(self.public))
        self.summary = self.root / 'summary.txt'

    def init(self, arm, name=None, protocol='claim-bindings-v2'):
        run = self.root / (name or arm)
        runtime.init_session(arm=arm, facts=self.facts, case_profile=self.profile,
            questions=self.questions, out=run, protocol=protocol)
        return run

    def final(self, bindings=None, unanswered=None):
        document = {'schema_version': 1, 'case_id': 'fixture', 'bindings': bindings or [],
                    'unanswered': unanswered or []}
        raw = json.dumps(document, indent=1).encode() + b'\n'
        summary = b'Model prose remains verbatim.\n```json\n' + raw + b'```  \n\n'
        self.summary.write_bytes(summary)
        return document, raw, summary

    def binding(self, cid, **extra):
        return {'candidate_id': cid, 'question_id': 'Q1', 'path': [],
                'part': 0, 'field': 'device_serial', **extra}

    def test_v2_neutral_tool_parity_notes_and_public_catalog_never_check_a(self):
        self.assertEqual(tools_for(), TOOLS)
        self.assertEqual(tools_for('claim-bindings-v2'), BINDING_TOOLS)
        a, c = self.init('A'), self.init('C')
        with patch('checker.check.check', side_effect=AssertionError('A active checker')), \
             patch('checker.claims.parse', side_effect=AssertionError('A semantic parser')), \
             patch('agent.answer_store.read_projection', side_effect=AssertionError('product answer read')):
            forms = runtime.call_tool(a, 'forms', {})
            self.assertIn('answer_projection', forms)
            self.assertEqual(forms, runtime.call_tool(c, 'forms', {}))
            for run in (a, c):
                plan = runtime.call_tool(run, 'plan', {})
                self.assertEqual(plan['facts_sha256'], runtime._binding(self.facts)['sha256'])
                self.assertNotIn('finding_ids', json.dumps(plan))
                self.assertNotIn('history', plan)
                self.assertEqual(plan['coverage']['inputs']['answers']['status'], 'not_supplied')
                updated = runtime.call_tool(run, 'update_question', {'question_id': 'Q1',
                    'searched': ['SELECT fixture records'], 'status': 'in_progress'})
                self.assertEqual(updated['questions'][0]['searched'], ['SELECT fixture records'])
                self.assertNotIn('finding_ids', json.dumps(updated))
                page = runtime.call_tool(run, 'inventory_page', {'question_id': 'Q1', 'page_size': 1})
                self.assertEqual(page['rows'][0][0], 1)
                self.assertTrue(page['exhausted'])
                for tool, args in [('update_question', {'question_id': 'Q1', 'finding_ids': ['A001']}),
                                   ('answer', {}), ('conclude', {}), ('collect', {})]:
                    with self.assertRaises(ValueError):
                        runtime.call_tool(run, tool, args)
            receipt = runtime.call_tool(a, 'check', {'question': 'Q1', 'claim': {'wrong': []}})
            self.assertEqual(receipt['status'], 'unverified')
        self.assertFalse((a / 'proposals.jsonl').exists())

    def test_legacy_default_retains_four_tool_contract(self):
        run = self.init('A', protocol='literal-v1')
        with self.assertRaises(ValueError):
            runtime.call_tool(run, 'plan', {})
        self.assertNotIn('answer_projection', runtime.call_tool(run, 'forms', {}))
        self.assertFalse((run / 'investigation.json').exists())

    def test_a_finalization_resolves_only_missing_hash_and_preserves_raw(self):
        run = self.init('A')
        claim = {'usbConnected': [1]}
        with patch('checker.check.check', side_effect=AssertionError('A checker')), \
             patch('verifier.verify.verify_run', side_effect=AssertionError('A verifier')):
            cid = runtime.call_tool(run, 'check', {'question': 'Q1', 'claim': claim})['candidate_id']
            document, raw, summary = self.final([self.binding(cid)])
            trial = runtime.finalize_session(run, summary=self.summary, status='completed')
        self.assertEqual(trial['protocol'], 'claim-bindings-v2')
        self.assertEqual(trial['projection']['status'], 'available')
        self.assertEqual((run / 'summary.md').read_bytes(), summary)
        self.assertEqual((run / 'bindings.raw.json').read_bytes(), raw)
        self.assertEqual(json.loads((run / 'bindings.json').read_text()), document)
        resolved = json.loads((run / 'bindings-resolved.json').read_text())
        self.assertEqual(resolved[0]['claim_sha256'], claim_digest(claim))
        self.assertNotIn('claim_sha256', document['bindings'][0])
        projected = json.loads((run / 'projected-answers.json').read_text())
        self.assertEqual(projected['answers'][0]['answer'], 'fixture-device')
        self.assertFalse((run / 'verification.json').exists())
        with self.assertRaises(ValueError):
            runtime.call_tool(run, 'forms', {})

    def test_wrong_provided_hash_is_retained_and_not_repaired(self):
        run = self.init('A')
        cid = runtime.call_tool(run, 'check', {'question': 'Q1', 'claim': {'usbConnected': [1]}})['candidate_id']
        self.final([self.binding(cid, claim_sha256='0' * 64)])
        trial = runtime.finalize_session(run, summary=self.summary, status='completed')
        self.assertEqual(trial['projection']['status'], 'available')
        self.assertEqual(json.loads((run / 'binding-resolution.json').read_text()), [])
        projection = json.loads((run / 'projection.json').read_text())
        self.assertEqual(projection['submission']['answers'][0]['status'], 'unknown')
        self.assertTrue(projection['unsupported'])

    def test_missing_invalid_binding_document_retains_unavailable_trial(self):
        for index, raw in enumerate((b'No final JSON document.\n', b'```json\n{"bad":true}\n```\n')):
            run = self.init('A', name='bad' + str(index))
            self.summary.write_bytes(raw)
            trial = runtime.finalize_session(run, summary=self.summary, status='completed')
            self.assertEqual(trial['projection']['status'], 'unavailable')
            self.assertEqual(trial['projection']['reason'], 'invalid_or_unavailable_binding_document')
            self.assertEqual((run / 'summary.md').read_bytes(), raw)
            self.assertTrue((run / 'seal.json').exists())
            self.assertTrue((run / 'trial.json').exists())
            self.assertFalse((run / 'projection.json').exists())

    def test_public_manifest_and_protocol_tampering_refused_before_tools(self):
        run = self.init('A')
        (run / 'run-manifest.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'manifest changed'):
            runtime.call_tool(run, 'forms', {})
        switched = self.init('A', name='switched')
        changed = json.loads((switched / 'session.json').read_text())
        changed['protocol'] = 'literal-v1'
        (switched / 'session.json').write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError, 'protocol'):
            runtime.call_tool(switched, 'forms', {})
        other = self.init('C')
        session = json.loads((other / 'session.json').read_text())
        session['protocol'] = 'unknown'
        (other / 'session.json').write_text(json.dumps(session))
        with self.assertRaisesRegex(ValueError, 'protocol'):
            runtime.call_tool(other, 'plan', {})

    def test_new_dependency_fingerprint_cannot_be_ignored(self):
        run = self.init('A')
        session = json.loads((run / 'session.json').read_text())
        self.assertIn('agent/inventory_pages.py', session['software']['source_sha256'])
        session['software']['source_sha256']['agent/inventory_pages.py'] = '0' * 64
        (run / 'session.json').write_text(json.dumps(session))
        with self.assertRaisesRegex(ValueError, 'implementation changed'):
            runtime.call_tool(run, 'forms', {})

    def test_c_projection_waits_for_independent_verification(self):
        for passed in (False, True):
            run = self.init('C', name='checked' + str(passed))
            # Synthetic recorded claim fixture; verification is explicitly mocked
            # to test runtime sequencing, not to assert that this is a certificate.
            proposal = {'finding_id': 'A001', 'question': 'Q1', 'claim': {'usbConnected': [1]}, 'status': 'verified'}
            (run / 'proposals.jsonl').write_text(json.dumps(proposal) + '\n')
            self.final([self.binding('A001')])
            verification = {'passed': passed, 'checked': 1, 'verified': int(passed), 'failed': int(not passed)}
            data = {'findings': []}
            from comparison.ablation.projection import project_c
            with patch('checker.export.bundle', return_value=data), \
                 patch('checker.report.render', return_value='Synthetic report'), \
                 patch('verifier.verify.verify_run', return_value=verification), \
                 patch('comparison.ablation.projection.project_c', wraps=project_c) as projector:
                trial = runtime.finalize_session(run, summary=self.summary, status='completed')
            self.assertEqual(projector.call_count, 0)
            if passed:
                self.assertEqual(trial['projection']['status'], 'unavailable')
                self.assertEqual(trial['projection']['reason'], 'invalid_or_unavailable_certificate_binding')
                self.assertFalse((run / 'projection.json').exists())
            else:
                self.assertEqual(trial['status'], 'failed')
                self.assertEqual(trial['projection']['status'], 'unavailable')
                self.assertEqual(trial['projection']['reason'], 'certificate_replay_failed')
                self.assertTrue((run / 'bindings.raw.json').exists())
                self.assertFalse((run / 'projection.json').exists())

    def test_real_c_projection_requires_exact_present_replayed_certificate(self):
        for mutation in ('none', 'missing', 'claim'):
            run = self.init('C', name='real-' + mutation)
            result = runtime.call_tool(run, 'check', {'question': 'Q1', 'claim': {'usbConnected': [1]}})
            self.assertEqual(result['status'], 'verified')
            self.final([self.binding(result['finding_id'])])
            if mutation == 'missing':
                (run / (result['finding_id'] + '.json')).unlink()
            elif mutation == 'claim':
                proposal_path = run / 'proposals.jsonl'
                proposal = json.loads(proposal_path.read_text())
                proposal['claim'] = {'searched': [1]}
                proposal_path.write_text(json.dumps(proposal) + '\n')
            trial = runtime.finalize_session(run, summary=self.summary, status='completed')
            self.assertTrue(trial['certificate_replay']['passed'])
            if mutation == 'none':
                self.assertEqual(trial['projection']['status'], 'available')
                self.assertEqual(json.loads((run / 'projected-answers.json').read_text())['answers'][0]['answer'], 'fixture-device')
            else:
                self.assertEqual(trial['projection']['status'], 'unavailable')
                self.assertEqual(trial['projection']['reason'], 'invalid_or_unavailable_certificate_binding')
                self.assertFalse((run / 'projection.json').exists())
            self.assertEqual((run / 'summary.md').read_bytes(), self.summary.read_bytes())

    def test_c_receipt_coverage_must_match_each_exact_certificate(self):
        from copy import deepcopy
        candidate = {'finding_id': 'A001', 'status': 'verified', 'claim': {'usbConnected': [1]}}
        bundle = {'findings': [deepcopy(candidate)]}
        verification = {'passed': True, 'checked': 1, 'verified': 1, 'failed': 0,
                        'findings': [{'finding_id': 'A001', 'problems': []}]}
        runtime._certified_candidates([candidate], bundle, verification)
        for receipts in ([], [{'finding_id': 'A002', 'problems': []}],
                         [{'finding_id': 'A001', 'problems': ['bad']}],
                         [{'finding_id': 'A001', 'problems': []}] * 2):
            changed = dict(verification, findings=receipts)
            with self.assertRaises(ValueError):
                runtime._certified_candidates([candidate], bundle, changed)
        with self.assertRaises(ValueError):
            runtime._certified_candidates([candidate], {'findings': bundle['findings'] * 2}, verification)

    def test_a_candidate_mutation_during_projection_never_publishes_available(self):
        run = self.init('A')
        cid = runtime.call_tool(run, 'check', {'question': 'Q1', 'claim': {'usbConnected': [1]}})['candidate_id']
        self.final([self.binding(cid)])
        from comparison.ablation.projection import project_a
        def mutate(*args, **kwargs):
            result = project_a(*args, **kwargs)
            with (run / 'candidates.jsonl').open('ab') as stream:
                stream.write(b'\n')
            return result
        with patch('comparison.ablation.projection.project_a', side_effect=mutate):
            trial = runtime.finalize_session(run, summary=self.summary, status='completed')
        self.assertEqual(trial['projection']['status'], 'unavailable')
        self.assertEqual(trial['projection']['reason'], 'invalid_or_unavailable_candidate_integrity')
        self.assertFalse((run / 'projection.json').exists())

    def test_failed_projection_closes_its_source_connection(self):
        run = self.init('A')
        cid = runtime.call_tool(run, 'check', {'question': 'Q1', 'claim': {'usbConnected': [1]}})['candidate_id']
        self.final([self.binding(cid)])
        source = Mock(spec=['_db'])
        source._db = Mock(spec=['close'])
        with patch('checker.facts.open_source', return_value=source), \
             patch('comparison.ablation.projection.project_a', side_effect=ValueError('projection fixture failure')):
            trial = runtime.finalize_session(run, summary=self.summary, status='completed')
        source._db.close.assert_called_once_with()
        self.assertEqual(trial['projection']['status'], 'unavailable')
        self.assertEqual(trial['projection']['failure_stage'], 'projection')

    def test_c_candidate_mutation_during_replay_is_retained_as_unavailable(self):
        run = self.init('C')
        result = runtime.call_tool(run, 'check', {'question': 'Q1', 'claim': {'usbConnected': [1]}})
        self.final([self.binding(result['finding_id'])])
        from verifier.verify import verify_run
        def mutate(*args, **kwargs):
            result = verify_run(*args, **kwargs)
            with (run / 'proposals.jsonl').open('ab') as stream:
                stream.write(b'\n')
            return result
        with patch('verifier.verify.verify_run', side_effect=mutate):
            trial = runtime.finalize_session(run, summary=self.summary, status='completed')
        self.assertTrue(trial['certificate_replay']['passed'])
        self.assertEqual(trial['projection']['status'], 'unavailable')
        self.assertEqual(trial['projection']['reason'], 'invalid_or_unavailable_candidate_integrity')
        self.assertTrue((run / 'bindings.raw.json').exists())
        self.assertFalse((run / 'projection.json').exists())


if __name__ == '__main__':
    unittest.main()
