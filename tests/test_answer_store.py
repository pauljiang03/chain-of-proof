"""Real certificates reach partial typed answers; forged views do not gain authority."""
import contextlib
from copy import deepcopy
import io
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import tempfile
import unittest
from unittest.mock import Mock, patch

from agent.answer_store import answer, read_projection, project_bundle, report_projection
from agent.investigation import Investigation
from agent.tools import Workbench
from app.report import render_html
from checker import check, export, report
from checker.facts import open_source
from eval.pipeline import Plan, evaluate

ROOT = Path(__file__).resolve().parent.parent
FACTS = ROOT / 'fixtures/sample_facts.json'


def public():
    return {'schema_version': 2, 'case_id': 'portable-other-case', 'title': 'Other case', 'questions': [
        {'id': 'DEVICES', 'prompt': 'Which devices and labels?', 'answer_schema': {
            'type': 'object', 'x-claim-scope': {'mode': 'unscoped_observation',
                'meaning': 'Synthetic context-free device observation; no selected source applicability asserted.'}, 'x-claim-row': {'mode': 'same_claim_part'}, 'properties': {'serial': {'type': 'string', 'x-claim-requirement': {
                'semantic_types': ['device_serial'], 'selectors': [{'form': 'usbConnected', 'field': 'device_serial'}],
                'meaning': 'Device serial recorded at connection', 'evidence_needed': 'A device connection record with its serial'}},
                'label': {'type': 'string', 'x-claim-requirement': {
                'semantic_types': ['volume_label'], 'meaning': 'Recorded volume label',
                'evidence_needed': 'A volume label record linked to this device'}}},
            'required': ['serial', 'label'], 'additionalProperties': False}},
        {'id': 'GAPS', 'prompt': 'What remains unknown?', 'answer_schema': {}}]}


class AnswerStore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.saved.cleanup)
        cls.certificate = check.check({'usbConnected': [4512]}, 'F1', open_source(FACTS),
                                     question='DEVICES', out_dir=Path(cls.saved.name))
        if cls.certificate['status'] != 'verified':
            raise AssertionError(cls.certificate)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        for source in Path(self.saved.name).iterdir():
            shutil.copyfile(source, self.path / source.name)
        Investigation(self.path).initialize(public())
        (self.path / 'questions.json').write_text(json.dumps(public()))
        self.binding = {'finding_id': 'F1', 'field': 'device_serial', 'path': ['serial']}

    def bundle(self):
        return export.bundle(self.path, 'Other case', case_metadata={'case_id': public()['case_id']})

    def test_partial_answer_retains_supported_field_without_inventing_missing_field(self):
        projected = answer(self.path, 'DEVICES', [self.binding])
        self.assertEqual(projected['submission']['answers'][0]['answer'], {'serial': 'SAMPLE-SERIAL-RM2'})
        self.assertEqual(projected['submission']['answers'][1]['status'], 'unknown')
        self.assertEqual(projected['leaves'][0]['candidate_id'], 'F1')
        self.assertEqual(read_projection(self.path), projected)
        run = self.bundle()
        self.assertEqual(project_bundle(run, public()), projected)
        self.assertIsNone(report_projection(run)[1])
        self.assertIn('Structured answers from claim fields', report.render(run))
        self.assertIn('href="#proof-f1"', render_html(run))

    def scoped_run(self, *, omit_source_key=None):
        from agent.run_manifest import file_binding
        directory = self.path / 'source-scoped'
        directory.mkdir()
        facts = json.loads(FACTS.read_text())
        origin = {'image': 'synthetic.dd', 'exhibit': 'SYNTHETIC-PC',
                  'source_snapshot': 'live', 'source_variant': 'primary'}
        for row in facts['facts']:
            row.setdefault('prov', {}).update(origin)
            if omit_source_key is not None:
                row['prov'].pop(omit_source_key, None)
        facts_path = self.path / 'scoped-facts.json'
        facts_path.write_text(json.dumps(facts))
        binding = file_binding(facts_path)
        manifest = {'inputs': {'facts': binding}}
        (directory / 'run-manifest.json').write_text(json.dumps(manifest))
        contract = public()
        contract['questions'][0]['answer_schema']['x-claim-scope'] = {
            'mode': 'source_records', 'origins': [origin], 'evidence_facts_sha256': binding['sha256']}
        Investigation(directory).initialize(contract)
        (directory / 'questions.json').write_text(json.dumps(contract))
        certificate = check.check({'usbConnected': [4512]}, 'F1', open_source(facts_path),
                                  question='DEVICES', out_dir=directory)
        self.assertEqual(certificate['status'], 'verified')
        return directory, facts_path, contract, binding['sha256']

    def test_scoped_direct_source_cleanup_and_borrowed_source_ownership(self):
        directory, facts_path, contract, digest = self.scoped_run()
        source = open_source(facts_path)

        class ResourceSource:
            def __init__(self):
                self._db = Mock()
            def get(self, ids):
                return source.get(ids)
            def string(self, sid):
                return source.string(sid)

        for fails in (False, True):
            owned = ResourceSource()
            with patch('agent.answer_store.open_source', return_value=owned):
                if fails:
                    with patch.object(owned, 'get', return_value={}):
                        result = answer(directory, 'DEVICES', [self.binding], preview=True)
                    self.assertFalse(result['valid'])
                else:
                    self.assertTrue(answer(directory, 'DEVICES', [self.binding], preview=True)['valid'])
            owned._db.close.assert_called_once_with()
        borrowed = ResourceSource()
        self.assertTrue(answer(directory, 'DEVICES', [self.binding], preview=True,
                               _evidence_source=borrowed, _evidence_facts_sha256=digest)['valid'])
        borrowed._db.close.assert_not_called()
        missing_digest = answer(directory, 'DEVICES', [self.binding], preview=True,
                                _evidence_source=borrowed)
        self.assertFalse(missing_digest['valid'])
        borrowed._db.close.assert_not_called()

    def test_source_scoped_answer_binds_actual_rows_and_replay_digest(self):
        directory, facts_path, contract, digest = self.scoped_run()
        bench = Workbench(facts_path, directory)
        with patch('agent.run_manifest.file_binding', wraps=__import__(
                'agent.run_manifest', fromlist=['file_binding']).file_binding) as measured:
            result = bench.answer('DEVICES', [self.binding])
            bench.answer('DEVICES', [self.binding], preview=True)
            self.assertEqual(measured.call_count, 1)
        self.assertEqual(result['submission']['answers'][0]['answer'], {'serial': 'SAMPLE-SERIAL-RM2'})
        stored = read_projection(directory)
        self.assertEqual(result['projection']['projection_sha256'], stored['projection']['projection_sha256'])
        self.assertEqual(result['projection']['evidence_facts_sha256'], digest)
        run = export.bundle(directory, 'Scoped synthetic case')
        self.assertEqual(project_bundle(run, contract), stored)
        with self.assertRaisesRegex(ValueError, 'actual verified'):
            project_bundle(run, contract, authority='independently_replayed')
        with self.assertRaisesRegex(ValueError, 'differs'):
            project_bundle(run, contract, authority='independently_replayed', evidence_facts_sha256='0' * 64)
        replayed = project_bundle(run, contract, authority='independently_replayed', evidence_facts_sha256=digest)
        self.assertEqual(replayed['submission'], stored['submission'])
        run['run_manifest']['inputs']['facts']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'differs'):
            project_bundle(run, contract)

    def test_source_scope_missing_snapshot_is_not_inferred_as_live(self):
        directory, facts_path, contract, digest = self.scoped_run(omit_source_key='source_snapshot')
        preview = answer(directory, 'DEVICES', [self.binding], preview=True)
        self.assertFalse(preview['valid'])
        self.assertEqual(preview['projection']['unsupported'][0]['reason'],
                         'claim_records_do_not_meet_public_scope')
        self.assertFalse((directory / 'answer-bindings.json').exists())

    def test_source_scoped_missing_manifest_and_changed_source_are_rejected(self):
        directory, facts_path, contract, digest = self.scoped_run()
        facts_path.write_text(facts_path.read_text() + ' ')
        with self.assertRaisesRegex(ValueError, 'actual evidence differs'):
            answer(directory, 'DEVICES', [self.binding])
        (directory / 'run-manifest.json').unlink()
        with self.assertRaisesRegex(ValueError, 'evidence changed'):
            answer(directory, 'DEVICES', [self.binding])
        self.assertFalse((directory / 'answer-bindings.json').exists())

    def test_coherently_forged_certificate_and_proposal_cannot_replace_source_scope(self):
        directory, facts_path, contract, digest = self.scoped_run()
        from checker.facts import Fact
        certificate_path = directory / 'F1.json'
        cert = json.loads(certificate_path.read_text())
        row = cert['cited_facts'][0]
        row['prov']['source_snapshot'] = 'forged-snapshot'
        row['row_sha256'] = Fact(row['id'], row['kind'], row['t'], row['res'],
                                row['obj'], row['aux'], row['prov']).row_sha256()
        certificate_path.write_text(json.dumps(cert))
        proposals_path = directory / 'proposals.jsonl'
        proposals = [json.loads(line) for line in proposals_path.read_text().splitlines()]
        for proposal in proposals:
            if proposal.get('finding_id') == 'F1':
                proposal['cited_facts'] = deepcopy(cert['cited_facts'])
        proposals_path.write_text(''.join(json.dumps(row) + '\n' for row in proposals))
        with self.assertRaisesRegex(ValueError, 'row differs from the bound evidence'):
            answer(directory, 'DEVICES', [self.binding])
        self.assertFalse((directory / 'answer-bindings.json').exists())

    def test_saved_coherent_row_survives_mixed_certificate_preview_and_update(self):
        contract = public()
        schema = contract['questions'][0]['answer_schema']
        schema['properties']['context'] = {
            'type': 'string', 'x-claim-requirement': {
                'semantic_types': ['connection_context'],
                'meaning': 'Connection context for this device observation',
                'evidence_needed': 'The context and serial from the same device connection claim'}}
        state_path = self.path / 'investigation.json'
        state = json.loads(state_path.read_text())
        state['questions'][0]['answer_schema'] = deepcopy(schema)
        state_path.write_text(json.dumps(state))
        (self.path / 'questions.json').write_text(json.dumps(contract))
        context = dict(self.binding, field='connection_context', path=['context'])
        saved = answer(self.path, 'DEVICES', [self.binding, context])
        self.assertEqual(len(saved['leaves']), 2)
        certificate = check.check({'usbConnected': [4510]}, 'F2', open_source(FACTS),
                                  question='DEVICES', out_dir=self.path)
        self.assertEqual(certificate['status'], 'verified')
        paths = [self.path / 'answer-bindings.json', self.path / 'projected-answers.json']
        before = [path.read_bytes() for path in paths]
        mixed = [self.binding, dict(context, finding_id='F2')]
        preview = answer(self.path, 'DEVICES', mixed, replace=True, preview=True)
        self.assertFalse(preview['valid'])
        self.assertFalse(preview['persisted'])
        self.assertIn('row_fields_require_same_claim_part',
                      [row['reason'] for row in preview['projection']['conflicts']])
        self.assertEqual([path.read_bytes() for path in paths], before)
        rejected = answer(self.path, 'DEVICES', mixed, replace=True)
        self.assertFalse(rejected['persisted'])
        self.assertEqual([path.read_bytes() for path in paths], before)
        self.assertEqual(read_projection(self.path), saved)
        self.assertEqual(project_bundle(self.bundle(), contract), saved)

    def test_malformed_mixed_batch_is_rejected_atomically(self):
        for invalid in [dict(self.binding, path='serial'), dict(self.binding, part=True),
                        dict(self.binding, finding_id='Foreign'),
                        dict(self.binding, claim_sha256='not-the-claim-hash')]:
            with self.assertRaises(ValueError):
                answer(self.path, 'DEVICES', [self.binding, invalid])
            self.assertFalse((self.path / 'answer-bindings.json').exists())
            self.assertFalse((self.path / 'projected-answers.json').exists())

    def test_mixed_partial_proposals_retain_only_supported_leaves_and_raw_diagnostics(self):
        contract = public()
        contract['questions'][0]['answer_schema']['properties']['application'] = {
            'type': 'string', 'x-claim-requirement': {
                'semantic_types': ['software_product'], 'meaning': 'Identified application product',
                'evidence_needed': 'Product identity evidence linked to the application'}}
        state_path = self.path / 'investigation.json'
        state = json.loads(state_path.read_text())
        state['questions'][0]['answer_schema'] = contract['questions'][0]['answer_schema']
        state_path.write_text(json.dumps(state))
        (self.path / 'questions.json').write_text(json.dumps(contract))
        stronger = dict(self.binding, path=['application'])
        result = answer(self.path, 'DEVICES', [self.binding, stronger])
        self.assertFalse(result['valid'])
        self.assertTrue(result['persisted'])
        self.assertEqual(result['update_outcome'], 'partial')
        self.assertEqual(result['submission']['answers'][0]['answer'], {'serial': 'SAMPLE-SERIAL-RM2'})
        self.assertEqual(result['unsupported'][0]['reason'], 'claim_role_does_not_meet_public_requirement')
        self.assertEqual(len(answer(self.path, 'DEVICES')['bindings']), 2)
        rebuilt = read_projection(self.path)
        self.assertEqual(rebuilt['submission'], result['submission'])
        self.assertEqual(rebuilt['unsupported'], result['unsupported'])
        self.assertEqual(project_bundle(self.bundle(), contract), rebuilt)
        before = (self.path / 'answer-bindings.json').read_bytes()
        rejected = answer(self.path, 'DEVICES', [stronger], replace=True)
        self.assertFalse(rejected['persisted'])
        self.assertEqual(rejected['update_outcome'], 'rejected')
        self.assertEqual((self.path / 'answer-bindings.json').read_bytes(), before)

    def test_preview_and_invalid_replacement_preserve_durable_partial_bytes(self):
        saved = answer(self.path, 'DEVICES', [self.binding])
        paths = [self.path / 'answer-bindings.json', self.path / 'projected-answers.json']
        before = [path.read_bytes() for path in paths]
        proposals = [dict(self.binding, path=['absent']),
                     dict(self.binding, path=['label']),
                     dict(self.binding, value='wrong'),
                     dict(self.binding, finding_id='Foreign')]
        for proposal in proposals:
            preview = answer(self.path, 'DEVICES', [proposal], replace=True, preview=True)
            self.assertFalse(preview['valid'])
            self.assertFalse(preview['persisted'])
            self.assertEqual([path.read_bytes() for path in paths], before)
        answer(self.path, 'DEVICES', [proposals[1]], replace=True)
        self.assertEqual([path.read_bytes() for path in paths], before)
        self.assertEqual(read_projection(self.path), saved)
        self.assertEqual(project_bundle(self.bundle(), public()), saved)

    def test_valid_preview_is_pure_and_audited(self):
        bench = Workbench(FACTS, self.path)
        preview = bench.answer('DEVICES', [self.binding], preview=True)
        self.assertTrue(preview['valid'])
        self.assertFalse((self.path / 'answer-bindings.json').exists())
        self.assertFalse((self.path / 'projected-answers.json').exists())
        events = [json.loads(line) for line in (self.path / 'audit.jsonl').read_text().splitlines()]
        self.assertEqual(events[-1]['tool'], 'answer')

    def test_conflicting_preview_does_not_hide_saved_sibling(self):
        answer(self.path, 'DEVICES', [self.binding])
        before = (self.path / 'answer-bindings.json').read_bytes()
        certificate = check.check({'usbConnected': [4510]}, 'F2', open_source(FACTS),
                                  question='DEVICES', out_dir=self.path)
        self.assertEqual(certificate['status'], 'verified')
        collision = dict(self.binding, finding_id='F2')
        result = answer(self.path, 'DEVICES', [collision], preview=True)
        self.assertFalse(result['valid'])
        self.assertEqual(result['projection']['conflicts'][0]['reason'], 'different_values_at_same_path')
        self.assertEqual((self.path / 'answer-bindings.json').read_bytes(), before)
        self.assertEqual(read_projection(self.path)['submission']['answers'][0]['answer'],
                         {'serial': 'SAMPLE-SERIAL-RM2'})

    def test_unannotated_legacy_binding_is_not_certified_on_rebuild(self):
        answer(self.path, 'DEVICES', [self.binding])
        run = self.bundle()
        unannotated = public()
        del unannotated['questions'][0]['answer_schema']['properties']['serial']['x-claim-requirement']
        run['investigation']['questions'] = deepcopy(unannotated['questions'])
        projected = project_bundle(run, unannotated)
        self.assertEqual(projected['submission']['answers'][0]['status'], 'unknown')
        self.assertEqual(projected['unsupported'][0]['reason'], 'missing_public_claim_requirement')
        self.assertIsNotNone(report_projection(run)[1])

    def test_foreign_refused_or_modified_certificate_cannot_supply_fields(self):
        for finding_id in ['Foreign', '../F1']:
            with self.assertRaises(ValueError):
                answer(self.path, 'DEVICES', [dict(self.binding, finding_id=finding_id)])
        cert = deepcopy(self.certificate)
        cert['cited_facts'][0]['obj_text'] = 'forged serial'
        (self.path / 'F1.json').write_text(json.dumps(cert))
        with self.assertRaisesRegex(ValueError, 'differs'):
            answer(self.path, 'DEVICES', [self.binding])
        self.assertFalse((self.path / 'answer-bindings.json').exists())

    def test_literal_mismatch_is_reported_and_never_repaired_into_an_answer(self):
        value = answer(self.path, 'DEVICES', [dict(self.binding, value='made-up')])
        self.assertEqual(value['submission']['answers'][0]['status'], 'unknown')
        self.assertEqual(value['unsupported'][0]['reason'], 'literal_value_mismatch_not_repaired')

    def test_replacement_is_explicit_and_idempotent_append_does_not_duplicate(self):
        answer(self.path, 'DEVICES', [self.binding])
        answer(self.path, 'DEVICES', [self.binding])
        self.assertEqual(len(answer(self.path, 'DEVICES')['bindings']), 1)
        cleared = answer(self.path, 'DEVICES', [], replace=True)
        self.assertEqual(cleared['submission']['answers'][0]['status'], 'unknown')

    def test_cached_projection_is_recomputed_and_report_tampering_is_unverified(self):
        answer(self.path, 'DEVICES', [self.binding])
        (self.path / 'projected-answers.json').write_text('{"forged":true}')
        run = self.bundle()
        run['answer_projection']['submission']['answers'][0]['answer']['serial'] = '<script>forged()</script>'
        self.assertIsNotNone(report_projection(run)[1])
        page = render_html(run)
        self.assertIn('Unverified supplied answer view', page)
        self.assertNotIn('<script>forged()', page)

    def test_binding_document_from_another_run_or_symlink_is_refused(self):
        answer(self.path, 'DEVICES', [self.binding])
        path = self.path / 'answer-bindings.json'
        doc = json.loads(path.read_text())
        doc['run_id'] = 'other-run'
        path.write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError, 'belong'):
            read_projection(self.path)
        path.unlink()
        path.symlink_to(self.path / 'F1.json')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            read_projection(self.path)

    def test_copied_strings_cannot_disagree_with_the_fixed_certificate_sentence(self):
        answer(self.path, 'DEVICES', [self.binding])
        run = self.bundle()
        run['findings'][0]['cited_facts'][0]['obj_text'] = 'forged serial'
        with self.assertRaisesRegex(ValueError, 'sentence'):
            project_bundle(run, public())

    def test_actual_tool_is_audited_and_exported_without_claiming_completeness(self):
        bench = Workbench(FACTS, self.path)
        projected = bench.answer('DEVICES', [self.binding])
        stored = read_projection(self.path)
        self.assertEqual(projected['view'], 'bounded_answer_update')
        self.assertEqual(projected['submission']['answers'], [stored['submission']['answers'][0]])
        self.assertEqual(projected['projection']['projection_sha256'], stored['projection']['projection_sha256'])
        self.assertEqual(len(stored['submission']['answers']), 2)
        self.assertIsNone(projected['projection']['evidence_facts_sha256'])
        run = self.bundle()
        self.assertEqual(run['audit']['status'], 'valid')
        self.assertEqual(run['answer_projection']['question_completeness'], 'not_established')

    def test_general_claim_adapter_reverifies_before_scoring_partial_answer(self):
        answer(self.path, 'DEVICES', [self.binding])
        reference = {'schema_version': 2, 'case_id': public()['case_id'], 'questions': [
            {'id': 'DEVICES', 'prompt': 'Which devices and labels?', 'expected': {'serial': 'SAMPLE-SERIAL-RM2', 'label': 'unknown-label'}},
            {'id': 'GAPS', 'prompt': 'What remains unknown?', 'expected': 'unknown'}]}
        plan = Plan(public()['case_id'], reference, public(), 'claims')
        with contextlib.redirect_stdout(io.StringIO()):
            result = evaluate(plan, self.bundle(), self.path / 'answers.json', self.path / 'results.json',
                              facts_path=FACTS, verification_output=self.path / 'verification.json')
        self.assertEqual(result['question_counts']['partial'], 1)
        self.assertEqual(result['question_counts']['unanswered'], 1)
        self.assertTrue(json.loads((self.path / 'verification.json').read_text())['passed'])

    @unittest.skipUnless(importlib.util.find_spec('deepagents'), 'optional API dependencies not installed')
    def test_real_offline_api_graph_recovers_bad_binding_then_saves_answer_and_pages(self):
        from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
        from langchain_core.messages import AIMessage
        from agent.run import run_deepagents

        class OfflineModel(FakeMessagesListChatModel):
            def bind_tools(self, tools, **kwargs):
                return self

        calls = [
            {'name': 'answer', 'id': 'bad', 'args': {'question_id': 'DEVICES', 'bindings': [dict(self.binding, finding_id='Foreign')]}},
            {'name': 'answer', 'id': 'valid', 'args': {'question_id': 'DEVICES', 'bindings': [self.binding]}},
            {'name': 'inventory_page', 'id': 'page', 'args': {'question_id': 'DEVICES', 'kinds': ['usbInsert'], 'page_size': 1}},
        ]
        model = OfflineModel(responses=[AIMessage(content='', tool_calls=[call]) for call in calls] + [AIMessage(content='done')])
        with patch.dict(os.environ, {'LANGSMITH_TRACING': 'false'}, clear=True), \
             patch.object(socket.socket, 'connect', side_effect=AssertionError('network forbidden')), \
             patch('deepagents.graph.resolve_model', return_value=model):
            result = run_deepagents('offline', self.path, str(FACTS), 'Public question only', timeout_s=15)
        self.assertEqual(result['ended'], 'success')
        self.assertEqual(read_projection(self.path)['submission']['answers'][0]['answer'], {'serial': 'SAMPLE-SERIAL-RM2'})
        events = [json.loads(line) for line in (self.path / 'audit.jsonl').read_text().splitlines()]
        self.assertEqual([e['tool'] for e in events], ['answer', 'answer', 'inventory_page'])
        self.assertEqual(events[0]['outcome'], 'error')


if __name__ == '__main__':
    unittest.main()
