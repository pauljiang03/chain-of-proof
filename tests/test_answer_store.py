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
from unittest.mock import patch

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
            'type': 'object', 'properties': {'serial': {'type': 'string'}, 'label': {'type': 'string'}},
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

    def test_actual_tool_is_audited_and_exported_without_claiming_completeness(self):
        bench = Workbench(FACTS, self.path)
        bench.answer('DEVICES', [self.binding])
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
