"""Public diagnostics preserve uncertainty and never repair draft answers."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from agent.coverage_plan import coverage_pass, MAX_NODES, MAX_PATHS
from agent.investigation import Investigation
from agent.tools import Workbench


def plan(schema=None):
    return {'schema_version': 1, 'case_id': 'fixture', 'facts_sha256': 'a' * 64,
            'questions': [{'id': 'Q1', 'prompt': 'Public question', 'work_status': 'not_started',
                           'searched': [], 'unresolved': ['pending source distinction'],
                           'answer_schema': schema or {'type': 'object', 'required': ['known', 'missing'],
                                                       'properties': {'known': {'type': 'string'}}}},
                          {'id': 'Q2', 'prompt': 'Other question', 'work_status': 'reviewed',
                           'searched': ['agent-reported query'], 'unresolved': [], 'answer_schema': {}}]}


def submission(value, status='answered'):
    return {'schema_version': 2, 'case_id': 'fixture',
            'answers': [{'question_id': 'Q1', 'status': status, 'answer': value}]}


class CoveragePlan(unittest.TestCase):
    def test_partial_fields_are_diagnosed_without_mutating_inputs(self):
        p, a = plan(), submission({'known': 'supported field'})
        saved = deepcopy((p, a))
        result = coverage_pass(p, a)
        self.assertEqual((p, a), saved)
        row = result['questions'][0]
        self.assertEqual(row['missing_required_fields'], ['/missing'])
        self.assertEqual(row['answer_status'], 'answered')
        self.assertEqual(result['counts']['not_started'], 1)
        self.assertEqual(result['counts']['no_recorded_searches'], 1)
        self.assertEqual(result['counts']['unresolved_work'], 1)
        self.assertEqual(result['counts']['answer_absent'], 1)
        self.assertNotIn('answer', row)

    def test_nested_objects_arrays_and_json_pointer_escaping(self):
        schema = {'type': 'object', 'required': ['rows'], 'properties': {
            'rows': {'type': 'array', 'items': {'type': 'object', 'required': ['a/b~c', 'nested'],
                    'properties': {'nested': {'type': 'object', 'required': ['time']}}}}}}
        result = coverage_pass(plan(schema), submission({'rows': [{'nested': {}}, {'a/b~c': False}]}))
        self.assertEqual(result['questions'][0]['missing_required_fields'],
                         ['/rows/0/a~1b~0c', '/rows/0/nested/time', '/rows/1/nested'])

    def test_empty_lists_null_and_false_are_present_legitimate_values(self):
        schema = {'type': 'object', 'required': ['rows', 'nullable', 'flag'], 'properties': {
            'rows': {'type': 'array', 'items': {'type': 'object', 'required': ['value']}},
            'nullable': {'type': ['object', 'null'], 'required': ['value']},
            'flag': {'type': 'boolean'}}}
        result = coverage_pass(plan(schema), submission({'rows': [], 'nullable': None, 'flag': False}))
        self.assertEqual(result['questions'][0]['missing_required_fields'], [])
        self.assertNotIn('schema_notes', result['questions'][0])
        self.assertIn('not necessarily inspected', result['limitation'])

    def test_absent_submission_absent_answer_unknown_and_missing_answer_differ(self):
        absent = coverage_pass(plan())
        self.assertEqual(absent['inputs']['answers']['status'], 'not_supplied')
        self.assertEqual(absent['counts']['answer_absent'], 0)
        unknown = coverage_pass(plan(), submission(None, 'unknown'))
        self.assertEqual(unknown['counts']['answer_unknown'], 1)
        self.assertEqual(unknown['counts']['answer_absent'], 1)
        self.assertEqual(unknown['questions'][0]['missing_required_fields'], [])
        unanswered = coverage_pass(plan(), submission(None, 'unanswered'))
        self.assertEqual(unanswered['counts']['answer_unknown'], 1)
        self.assertEqual(unanswered['questions'][0]['answer_status'], 'unanswered')
        a = submission(None)
        del a['answers'][0]['answer']
        self.assertEqual(coverage_pass(plan(), a)['counts']['answer_missing'], 1)

    def test_invalid_or_foreign_submission_is_not_partially_accepted(self):
        for mutate in (lambda a: a.update(case_id='other'),
                       lambda a: a['answers'].append(deepcopy(a['answers'][0])),
                       lambda a: a['answers'][0].update(question_id='foreign'),
                       lambda a: a.update(schema_version=1)):
            a = submission({'known': 'value'})
            mutate(a)
            result = coverage_pass(plan(), a)
            self.assertEqual(result['inputs']['answers']['status'], 'invalid')
            self.assertTrue(all(row['answer_status'] == 'invalid' for row in result['questions']))
            self.assertEqual(result['counts']['answer_absent'], 0)
        self.assertEqual(coverage_pass({'questions': []})['status'], 'unavailable')
        for invalid_id in ('', '   ', 'q' * 129):
            p = plan()
            p['questions'][0]['id'] = invalid_id
            self.assertEqual(coverage_pass(p)['status'], 'unavailable')
            a = submission({})
            a['answers'][0]['question_id'] = invalid_id
            self.assertEqual(coverage_pass(plan(), a)['inputs']['answers']['status'], 'invalid')

    def test_inventory_cursor_is_actionable_and_stale_state_is_explicit(self):
        inventory = {'status': 'recorded', 'evidence_sha256': 'a' * 64, 'traversals': [
            {'question_id': 'Q1', 'kinds': ['webVisit'], 'exhibits': ['image'], 'page_size': 50,
             'next_cursor': 'opaque:next', 'exhausted': False, 'rows_returned': 50}]}
        saved = deepcopy(inventory)
        result = coverage_pass(plan(), inventory_progress=inventory)
        self.assertEqual(result['counts']['pending_inventory'], 1)
        self.assertEqual(result['questions'][0]['pending_inventory'], [
            {'kinds': ['webVisit'], 'exhibits': ['image'], 'page_size': 50, 'next_cursor': 'opaque:next'}])
        self.assertEqual(saved, inventory)
        inventory['evidence_sha256'] = 'b' * 64
        result = coverage_pass(plan(), inventory_progress=inventory)
        self.assertEqual(result['inputs']['inventory']['status'], 'invalid')
        self.assertEqual(result['counts']['pending_inventory'], 0)
        inventory['evidence_sha256'] = 'a' * 64
        inventory['traversals'][0]['question_id'] = []
        self.assertEqual(coverage_pass(plan(), inventory_progress=inventory)['inputs']['inventory']['status'], 'invalid')

    def test_inventory_accepts_more_than_sixty_four_bounded_traversals(self):
        traversals = [{'question_id': 'Q1', 'kinds': [str(i)], 'exhibits': None, 'page_size': 50,
                       'next_cursor': f'cursor:{i}', 'exhausted': False} for i in range(65)]
        result = coverage_pass(plan(), inventory_progress={'status': 'recorded',
                               'evidence_sha256': 'a' * 64, 'traversals': traversals})
        self.assertEqual(result['inputs']['inventory']['status'], 'recorded')
        self.assertEqual(result['counts']['pending_inventory'], 65)

    def test_alternatives_and_unsupported_schema_are_conservative(self):
        schema = {'type': 'object', 'required': ['common'], 'oneOf': [
            {'required': ['left']}, {'required': ['right']}], 'customPresenceRule': True}
        result = coverage_pass(plan(schema), submission({}))
        row = result['questions'][0]
        self.assertEqual(row['missing_required_fields'], ['/common'])
        self.assertTrue(any('ambiguous' in note for note in row['schema_notes']))
        self.assertTrue(any('Unsupported' in note for note in row['schema_notes']))
        self.assertTrue(any('only directly declared' in note for note in row['schema_notes']))

    def test_non_presence_constraints_are_globally_unvalidated_without_actionable_warning(self):
        schema = {'type': 'object', 'required': ['value'], 'additionalProperties': False,
                  'minProperties': 2, 'properties': {'value': {'type': 'string', 'enum': ['allowed'],
                      'format': 'date-time', 'minLength': 10, 'maxLength': 12, 'pattern': '^a',
                      'minimum': 3, 'maximum': 5}}}
        result = coverage_pass(plan(schema), submission({'value': False}))
        row = result['questions'][0]
        self.assertEqual(row['missing_required_fields'], [])
        self.assertNotIn('schema_notes', row)
        self.assertNotIn('schema_review_needed', row['diagnostics'])
        self.assertIn('not validated', result['limitation'])

    def test_nodes_depth_and_missing_paths_are_bounded(self):
        result = coverage_pass(plan({'required': [str(i) for i in range(MAX_PATHS + 5)]}), submission({}))
        self.assertEqual(len(result['questions'][0]['missing_required_fields']), MAX_PATHS)
        self.assertTrue(result['questions'][0]['schema_notes'])
        schema, value = {'type': 'object'}, {}
        for _ in range(30):
            schema, value = {'properties': {'child': schema}}, {'child': value}
        self.assertTrue(coverage_pass(plan(schema), submission(value))['questions'][0]['schema_notes'])
        schema = {'items': {'required': ['missing']}}
        result = coverage_pass(plan(schema), submission([{}] * (MAX_NODES + 1)))
        self.assertLessEqual(len(result['questions'][0]['missing_required_fields']), MAX_PATHS)
        self.assertTrue(result['questions'][0]['schema_notes'])


class PlanIntegration(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.run = self.root / 'run'
        p = plan()
        public = {'schema_version': 2, 'case_id': 'fixture', 'title': 'Fixture', 'questions': [
            {key: q[key] for key in ('id', 'prompt', 'answer_schema')} for q in p['questions']]}
        Investigation(self.run).initialize(public)
        facts = self.root / 'facts.json'
        facts.write_text(json.dumps({'strings': {'1': 'fixture'}, 'facts': [
            {'id': 1, 'kind': 'usbInsert', 't': 0, 'res': 0, 'obj': 1, 'aux': 1,
             'prov': {'artifact': 'fixture'}}]}))
        self.bench = Workbench(facts, self.run)
        self.addCleanup(self.bench._db.close)

    def test_plan_uses_safe_projection_and_preserves_core_without_history(self):
        module = types.ModuleType('agent.answer_store')
        calls = []
        module.read_projection = lambda run: (calls.append(run) or {'submission': submission({'known': 'partial'})})
        state = Investigation(self.run).snapshot()
        saved = (self.run / 'investigation.json').read_bytes()
        # A malicious cached projection is not read by Workbench.plan.
        (self.run / 'projected-answers.json').write_text('invalid cache')
        with patch.dict(sys.modules, {'agent.answer_store': module}):
            result = self.bench.plan()
        self.assertEqual(calls, [self.run])
        self.assertEqual(result['coverage']['questions'][0]['missing_required_fields'], ['/missing'])
        self.assertEqual({k: v for k, v in result.items() if k != 'coverage'},
                         {k: v for k, v in state.items() if k != 'history'})
        self.assertEqual((self.run / 'investigation.json').read_bytes(), saved)

    def test_bad_projection_and_inventory_do_not_lose_core_plan(self):
        module = types.ModuleType('agent.answer_store')
        def bad_read(run):
            raise ValueError('stale binding')
        module.read_projection = bad_read
        with patch.dict(sys.modules, {'agent.answer_store': module}), \
                patch('agent.inventory_pages.inventory_progress', side_effect=ValueError('stale inventory')):
            result = self.bench.plan()
        self.assertEqual(len(result['questions']), 2)
        self.assertEqual(result['coverage']['inputs']['answers']['status'], 'unavailable')
        self.assertEqual(result['coverage']['inputs']['inventory']['status'], 'unavailable')
        self.assertTrue(all(q['answer_status'] == 'unavailable' for q in result['coverage']['questions']))

    def test_safe_reader_none_means_no_binding_sidecar(self):
        module = types.ModuleType('agent.answer_store')
        module.read_projection = lambda run: None
        with patch.dict(sys.modules, {'agent.answer_store': module}):
            result = self.bench.plan()
        self.assertEqual(result['coverage']['inputs']['answers']['status'], 'not_supplied')
        self.assertEqual(result['coverage']['counts']['answer_absent'], 0)

    def test_missing_projection_module_is_only_not_supplied_case(self):
        import builtins
        original = builtins.__import__
        def absent(name, *args, **kwargs):
            if name == 'agent.answer_store':
                raise ModuleNotFoundError('absent optional module', name=name)
            return original(name, *args, **kwargs)
        with patch('builtins.__import__', side_effect=absent):
            self.assertEqual(self.bench.plan()['coverage']['inputs']['answers']['status'], 'not_supplied')
        def dependency_missing(name, *args, **kwargs):
            if name == 'agent.answer_store':
                raise ModuleNotFoundError('broken dependency', name='missing_dependency')
            return original(name, *args, **kwargs)
        with patch('builtins.__import__', side_effect=dependency_missing):
            self.assertEqual(self.bench.plan()['coverage']['inputs']['answers']['status'], 'unavailable')


if __name__ == '__main__':
    unittest.main()
