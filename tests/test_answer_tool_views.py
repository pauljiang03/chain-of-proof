"""Native answer outputs are bounded; full store documents remain unchanged."""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from agent import answer_store, answer_views
from agent.investigation import Investigation
from agent.mcp_server import call, tools_for
from agent.tools import Workbench

ROOT = Path(__file__).resolve().parents[1]
FACTS = ROOT / 'fixtures/sample_facts.json'
ACTUAL_EVIDENCE_CONTEXT = answer_store._evidence_context


def public():
    return {'schema_version': 2, 'case_id': 'synthetic-native-answer-views', 'questions': [
        {'id': q, 'prompt': 'Synthetic question ' + q, 'answer_schema': {'type': 'object'}}
        for q in ('Q1', 'Q2')]}


class AnswerToolViews(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        Investigation(self.root).initialize(public())
        self.bench = Workbench(FACTS, self.root)
        self.addCleanup(self.bench._db.close)
        self.value = 'synthetic oversized value ' + '\u2603' * 2500
        self.project_calls = []

        def certificates(directory, bindings):
            return {b['candidate_id']: {'claim': {'usbConnected': [4512]}} for b in bindings}

        def project(state, document, certs, **kwargs):
            # Isolate native output policy from kernel/answer semantics. These
            # deterministic full documents stand in for the trusted projector.
            self.project_calls.append(deepcopy(document))
            leaves = [dict(b, binding_index=i, value=self.value, semantic_type='synthetic')
                      for i, b in enumerate(document['bindings'])]
            return {'submission': {'answers': [
                {'question_id': q, 'status': 'answered', 'answer': [self.value for leaf in leaves
                                                                 if leaf['question_id'] == q]}
                for q in ('Q1', 'Q2')]}, 'leaves': leaves, 'unsupported': [], 'conflicts': [],
                'projection': {'evidence_facts_sha256': kwargs.get('evidence_facts_sha256'),
                               'public_sha256': 'a' * 64, 'projection_sha256': 'b' * 64},
                'question_completeness': 'not_established'}

        for name, effect in (('_certificates', certificates), ('_project', project)):
            patcher = patch('agent.answer_store.' + name, side_effect=effect)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch('agent.answer_store._evidence_context', return_value=hashlib.sha256(FACTS.read_bytes()).hexdigest())
        patcher.start()
        self.addCleanup(patcher.stop)

    def bindings(self, n):
        return [dict(finding_id='F1', field='device_serial', path=['records', i]) for i in range(n)]

    def seed(self):
        answer_store.answer(self.root, 'Q1', self.bindings(237))
        answer_store.answer(self.root, 'Q2', self.bindings(109))

    def durable(self):
        return {name: (self.root / name).read_bytes() for name in
                ('answer-bindings.json', 'projected-answers.json') if (self.root / name).exists()}

    def all_pages(self, section, size=17):
        page = self.bench.answer('Q1', section=section, page_size=size)
        rows, token = [], page['state_token']
        while True:
            self.assertEqual(page['view'], 'bounded_answer_inspection')
            self.assertLess(len(json.dumps(page)), 65_000)
            rows.extend(page[section])
            offset = page['page']['next_offset']
            if offset is None:
                return rows, page
            page = self.bench.answer('Q1', section=section, offset=offset, page_size=size, state_token=token)

    def test_every_binding_and_leaf_is_reachable_without_store_mutation(self):
        self.seed()
        before = self.durable()
        bindings, page = self.all_pages('bindings')
        self.assertEqual(page['page']['total'], 237)
        self.assertEqual([b['path'][-1] for b in bindings], list(range(237)))
        leaves, page = self.all_pages('leaves')
        self.assertEqual(len(leaves), 237)
        self.assertTrue(all(leaf['view'] == 'omitted_oversize_value' for leaf in leaves))
        self.assertEqual([leaf['record_identity']['binding_index'] for leaf in leaves], list(range(237)))
        self.assertEqual(before, self.durable())
        full = answer_store.read_projection(self.root)
        self.assertEqual(len(full['leaves']), 346)
        self.assertTrue(all(leaf['value'] == self.value for leaf in full['leaves']))

    def test_mutation_and_preview_return_selected_question_bounded_views(self):
        self.seed()
        original = answer_store.read_projection(self.root)
        before = self.durable()
        preview = self.bench.answer('Q1', self.bindings(238), preview=True)
        self.assertTrue(preview['valid'])
        self.assertFalse(preview['persisted'])
        self.assertEqual(preview['counts']['leaves'], 238)
        self.assertEqual(before, self.durable())
        result = self.bench.answer('Q1', self.bindings(238))
        self.assertEqual(result['view'], 'bounded_answer_update')
        self.assertTrue(result['persisted'])
        self.assertEqual(result['counts']['leaves'], 238)
        self.assertEqual(len(result['leaves']), 5)
        self.assertEqual(result['leaves_omitted_count'], 233)
        self.assertLess(len(json.dumps(result)), 15_000)
        self.assertNotIn('Q2', json.dumps(result))
        self.assertEqual(len(answer_store.read_projection(self.root)['leaves']), 347)
        self.assertEqual(len(original['leaves']), 346)
        persisted = json.loads((self.root / 'projected-answers.json').read_text())
        self.assertEqual(persisted, answer_store.read_projection(self.root))

    def test_oversize_descriptor_never_claims_exact_or_null(self):
        value = {'value': self.value}
        result = answer_views.bounded(value)
        raw = json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode()
        self.assertFalse(result['exact_value_included'])
        self.assertFalse(result['preview_is_exact_value'])
        self.assertEqual(result['json_bytes'], len(raw))
        self.assertEqual(result['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertNotIn('value', result)
        self.assertEqual(answer_views.bounded(None), None)  # genuine source null stays null

    def test_invalid_paging_is_rejected_before_any_store_write_including_preview(self):
        for params in ({'offset': -1}, {'offset': True}, {'page_size': True}, {'page_size': 0},
                       {'page_size': 101}, {'page_size': 1.5}, {'section': 'all'},
                       {'state_token': 'bad'}, {'offset': 1}):
            with self.subTest(params=params), patch('agent.answer_store.answer') as store:
                with self.assertRaises(ValueError):
                    self.bench.answer('Q1', **params)
                store.assert_not_called()
        for params in ({'offset': 0}, {'page_size': 1}, {'section': 'bindings'}, {'state_token': 'a' * 64}):
            for preview in (False, True):
                with self.subTest(params=params, preview=preview), patch('agent.answer_store.answer') as store:
                    with self.assertRaisesRegex(ValueError, 'inspection-only'):
                        self.bench.answer('Q1', [], preview=preview, **params)
                    store.assert_not_called()
        self.assertEqual(self.durable(), {})

    def test_tokens_bind_state_and_question_and_out_of_range_offsets_refuse(self):
        self.seed()
        first = self.bench.answer('Q1', page_size=2)
        token = first['state_token']
        with self.assertRaisesRegex(ValueError, 'another question'):
            self.bench.answer('Q2', state_token=token)
        with self.assertRaisesRegex(ValueError, 'exceeds'):
            self.bench.answer('Q1', offset=238, state_token=token)
        self.bench.answer('Q1', self.bindings(238))
        with self.assertRaisesRegex(ValueError, 'stale'):
            self.bench.answer('Q1', offset=2, state_token=token)

    def test_catalog_and_schema_diagnostics_are_explicitly_paged_and_complete(self):
        rows, page = self.all_pages('field_catalog', 100)
        self.assertEqual(len(rows), page['counts']['field_catalog'])
        roles = {row['path'][1] for row in rows if row['path'][0] == 'attribute_roles'}
        from checker.catalog import ROLES
        self.assertEqual(roles, set(ROLES))
        self.assertTrue(any(row['path'][:2] == ['forms', 'attributeTuple'] for row in rows))
        rows, page = self.all_pages('field_requirements')
        self.assertEqual(len(rows), page['page']['total'])
        self.assertTrue(rows)

    def test_diagnostic_samples_are_bounded_and_selected_q_only(self):
        rows = [dict(binding={'question_id': 'Q1'}, reason='synthetic', value=self.value) for _ in range(300)]
        full = {'preview': True, 'valid': False, 'persisted': False, 'projection': {
            'submission': {'answers': [{'question_id': 'Q2', 'answer': self.value}]},
            'unsupported': rows + [dict(binding={'question_id': 'Q2'}, reason='other')],
            'conflicts': [], 'leaves': []}}
        result = answer_views.mutation_view(full, 'Q1')
        self.assertFalse(result['valid'])
        self.assertEqual(result['counts']['unsupported'], 300)
        self.assertEqual(result['unsupported_omitted_count'], 295)
        self.assertEqual(len(result['unsupported']), 5)
        self.assertNotIn('Q2', json.dumps(result))
        self.assertLess(len(json.dumps(result)), 10_000)

    def test_inspection_loads_one_coherent_document_under_one_lock(self):
        self.seed()
        active, events = [False], []
        original_lock, original_load = Investigation._locked, Investigation._load
        original_document = answer_store._document
        original_project = answer_store._project.side_effect
        original_context = answer_store._evidence_context.side_effect
        digest = hashlib.sha256(FACTS.read_bytes()).hexdigest()

        @contextmanager
        def tracked_lock(planner):
            self.assertFalse(active[0])
            with original_lock(planner):
                active[0] = True
                events.append('lock')
                try:
                    yield
                finally:
                    active[0] = False
                    events.append('unlock')

        def load(planner):
            self.assertTrue(active[0])
            events.append('state')
            return original_load(planner)

        def document(path, state):
            self.assertTrue(active[0])
            events.append('document')
            return original_document(path, state)

        def context(*args, **kwargs):
            self.assertTrue(active[0])
            events.append('source')
            return digest

        def project(*args, **kwargs):
            self.assertTrue(active[0])
            events.append('project')
            return original_project(*args, **kwargs)

        with patch.object(Investigation, '_locked', tracked_lock), \
             patch.object(Investigation, '_load', load), \
             patch('agent.answer_store._document', side_effect=document), \
             patch('agent.answer_store.answer', side_effect=AssertionError('no separate metadata read')), \
             patch('agent.answer_store.read_projection', side_effect=AssertionError('no separate projection read')):
            answer_store._project.side_effect = project
            answer_store._evidence_context.side_effect = context
            try:
                result = self.bench.answer('Q1', page_size=100)
            finally:
                answer_store._project.side_effect = original_project
                answer_store._evidence_context.side_effect = original_context
        self.assertEqual(events, ['lock', 'state', 'document', 'source', 'project', 'unlock'])
        self.assertEqual(result['counts']['bindings'], result['counts']['leaves'])
        self.assertEqual(result['counts']['bindings'], 237)

    def test_cached_workbench_context_skips_fact_rehash_and_direct_snapshot_verifies_file(self):
        self.seed()
        digest = hashlib.sha256(FACTS.read_bytes()).hexdigest()
        for filename in ('investigation.json', 'answer-bindings.json'):
            path = self.root / filename
            document = json.loads(path.read_text())
            document['facts_sha256'] = digest
            path.write_text(json.dumps(document))
        (self.root / 'run-manifest.json').write_text(json.dumps({
            'inputs': {'facts': {'path': str(FACTS), 'sha256': digest}}}))
        from agent.run_manifest import file_binding
        from checker.facts import open_source
        with patch('agent.answer_store._evidence_context', wraps=ACTUAL_EVIDENCE_CONTEXT), \
             patch('agent.answer_store._scoped', return_value=True), \
             patch('agent.run_manifest.file_binding', wraps=file_binding) as hashed, \
             patch('agent.answer_store.open_source', wraps=open_source) as opened:
            first = self.bench.answer('Q1', page_size=2)
            self.bench.answer('Q1', offset=2, page_size=2, state_token=first['state_token'])
            self.assertEqual(hashed.call_count, 1, 'only the first Workbench binding hashes facts')
            opened.assert_not_called()
            # No trusted source pair: retain ordinary file hash/open checks.
            answer_store._inspection_snapshot(self.root, 'Q1')
            self.assertEqual(hashed.call_count, 2)
            self.assertEqual(opened.call_count, 1)

    def test_workbench_refuses_source_stat_change_during_inspection(self):
        self.bench._inventory_evidence_sha256 = hashlib.sha256(FACTS.read_bytes()).hexdigest()
        initial = self.bench._inventory_initial_stat
        with patch.object(self.bench, '_inventory_stat', side_effect=[initial, object()]):
            with self.assertRaisesRegex(ValueError, 'changed during answer inspection'):
                self.bench.answer('Q1')
        self.assertEqual(self.durable(), {})

    def test_mcp_preview_and_paging_are_exposed_and_routed(self):
        schema = tools_for(['answer'])[0]['inputSchema']
        self.assertIn('preview', schema['properties'])
        for name in ('section', 'offset', 'page_size', 'state_token'):
            self.assertIn(name, schema['properties'])
        bench = Mock()
        bench.answer.return_value = {'view': 'bounded_answer_update', 'preview': True}
        args = dict(question_id='Q1', bindings=[], preview=True)
        self.assertTrue(json.loads(call(bench, 'answer', args))['preview'])
        bench.answer.assert_called_once_with(**args)
        with self.assertRaises(ValueError):
            call(bench, 'answer', dict(question_id='Q1', unreviewed=True))


if __name__ == '__main__':
    unittest.main()
