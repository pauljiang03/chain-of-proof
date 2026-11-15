"""Common public anyOf paths are projected without selecting or repairing a branch."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from agent.answer_projection import project_answers
from comparison.ablation.projection import project_a, project_b
from tests.test_ablation_projection import replay
from tests.test_answer_projection import Source, bind, candidate


def public(schema):
    return {'schema_version': 2, 'case_id': 'new-public-case', 'questions': [
        {'id': 'inventory', 'prompt': 'What do the records name?', 'answer_schema': schema}]}


def object_schema(**fields):
    return {'type': 'object', 'properties': fields, 'additionalProperties': False}


class CommonAnyOfProjection(unittest.TestCase):
    def setUp(self):
        self.source = Source()
        self.row = candidate('P1', {'usbConnected': [1]})

    def project(self, schema, path, *, row=None, field='device_serial', **extra):
        row = row or self.row
        return project_answers(public(schema), [row],
            [bind(row, 'inventory', path, field, **extra)], self.source)

    def test_common_nested_fields_with_nullable_variants_preserve_partial_values(self):
        variants = [object_schema(serial={'type': 'string'}, time={'type': 'string'}),
                    object_schema(serial={'type': 'string'}, time={'type': ['string', 'null']})]
        for branch in variants:
            branch['properties']['unobserved'] = {'type': 'string'}
            branch['required'] = ['serial', 'time', 'unobserved']
        schema = object_schema(records={'type': 'array', 'items': {'anyOf': variants}})
        contract = public(schema)
        bindings = [bind(self.row, 'inventory', ['records', 0, 'serial'], 'device_serial'),
                    bind(self.row, 'inventory', ['records', 0, 'time'], 'recorded_time_us', format='utc_iso')]
        before = deepcopy((contract, self.row, bindings))
        with patch('checker.check.run_kernel', side_effect=AssertionError('no gate')):
            result = project_answers(contract, [self.row], bindings, self.source)
        self.assertEqual(result['submission']['answers'][0]['answer'],
                         {'records': [{'serial': 'DEVICE-A', 'time': '1970-01-01T00:01:40Z'}]})
        self.assertFalse(result['unsupported'])
        self.assertEqual((contract, self.row, bindings), before)
        variants.reverse()
        reverse = project_answers(contract, [self.row], bindings, self.source)
        self.assertEqual(reverse['submission'], result['submission'])
        self.assertEqual(reverse['leaves'], result['leaves'])

    def test_branch_exclusive_paths_are_refused_even_with_permissive_other_branch(self):
        for other in ({'type': 'object', 'additionalProperties': True}, {}, {'type': 'null'}):
            with self.subTest(other=other):
                result = self.project({'anyOf': [object_schema(serial={'type': 'string'}), other]}, ['serial'])
                self.assertEqual(result['submission']['answers'][0]['status'], 'unknown')
                self.assertTrue(result['unsupported'])
        result = self.project({'anyOf': [{'type': 'array', 'items': {'type': 'string'}},
                                        {'type': 'array'}]}, [0])
        self.assertEqual(result['unsupported'][0]['reason'], 'path_not_common_to_public_schema_anyof')

    def test_leaf_must_satisfy_every_type_without_branch_choice_or_claim_repair(self):
        for alternatives in ([{'type': 'string'}, {'type': 'integer'}],
                             [{'type': 'string'}, {'type': 'null'}]):
            result = self.project({'anyOf': alternatives}, [])
            self.assertEqual(result['unsupported'][0]['reason'], 'value_type_does_not_match_public_schema')
        wrong_count = candidate('COUNT', {'exactly': ['usbInsert', 999]})
        result = self.project({'anyOf': [{'type': 'number'}, {'type': 'integer'}]}, [],
                              row=wrong_count, field='count')
        self.assertEqual(result['submission']['answers'][0]['answer'], 999)
        wrong_kind = candidate('WRONG_KIND', {'usbConnected': [3]})
        result = self.project({'anyOf': [object_schema(serial={'type': 'string'}),
                                        object_schema(serial={'type': ['string', 'null']})]},
                              ['serial'], row=wrong_kind)
        self.assertEqual(result['submission']['answers'][0]['answer'], {'serial': 'query text'})

    def test_sibling_constraints_are_retained(self):
        schema = {'type': 'integer', 'anyOf': [{'type': 'string'}, {'type': ['string', 'integer']}]}
        result = self.project(schema, [])
        self.assertEqual(result['unsupported'][0]['reason'], 'value_type_does_not_match_public_schema')
        schema = object_schema(serial={'type': 'string'})
        schema['anyOf'] = [object_schema(serial={'type': 'string'}),
                           object_schema(serial={'type': ['string', 'null']})]
        result = self.project(schema, ['serial'])
        self.assertEqual(result['submission']['answers'][0]['answer'], {'serial': 'DEVICE-A'})

    def test_refs_other_unions_and_malformed_alternatives_stay_unsupported(self):
        for unsupported in ({'$ref': '#/anywhere'}, {'$dynamicRef': '#/anywhere'},
                            {'$recursiveRef': '#/anywhere'}, {'oneOf': [{'type': 'string'}]},
                            {'allOf': [{'type': 'string'}]}):
            result = self.project({'anyOf': [{'type': 'string'}, unsupported]}, [])
            self.assertEqual(result['unsupported'][0]['reason'], 'unsupported_schema_reference_or_union')
        for alternatives in ([], {}, [True], [{'type': 'string'}] * 33):
            result = self.project({'anyOf': alternatives}, [])
            self.assertTrue(result['unsupported'])
            self.assertEqual(result['submission']['answers'][0]['status'], 'unknown')

    def test_nested_alternatives_and_work_limits(self):
        result = self.project({'anyOf': [{'type': 'string'},
                                        {'anyOf': [{'type': 'string'}, {'type': ['string', 'null']}]}]}, [])
        self.assertEqual(result['submission']['answers'][0]['answer'], 'DEVICE-A')
        deep = {'type': 'string'}
        for _ in range(34):
            deep = {'anyOf': [deep]}
        broad = {'anyOf': [{'anyOf': [{'type': 'string'}] * 32}] * 32}
        for schema in (deep, broad):
            result = self.project(schema, [])
            self.assertEqual(result['unsupported'][0]['reason'], 'public_schema_traversal_limit')
        result = self.project({}, ['field'] * 17)
        self.assertIn('at most 16', result['unsupported'][0]['reason'])

    def test_b_uses_frozen_values_and_cannot_unhide_anyof_conflicts(self):
        schema = {'anyOf': [object_schema(serial={'type': 'string'}),
                            object_schema(serial={'type': ['string', 'null']})]}
        wrong = candidate('P2', {'usbConnected': [3]})
        bindings = [bind(row, 'inventory', ['serial'], 'device_serial') for row in (self.row, wrong)]
        a = project_a(public(schema), [self.row, wrong], bindings, self.source)
        self.assertTrue(a['conflicts'])
        with patch.object(self.source, 'get', side_effect=AssertionError('B must not reread evidence')):
            b = project_b(a, [replay(self.row, 'verified'), replay(wrong, 'rejected')])
        self.assertEqual(a['submission'], b['submission'])
        self.assertEqual(b['submission']['answers'][0]['status'], 'unknown')
        self.assertEqual(a['projection'], b['projection'])


if __name__ == '__main__':
    unittest.main()
