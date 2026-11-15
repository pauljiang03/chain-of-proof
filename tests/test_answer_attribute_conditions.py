"""Exact same-atomic-part attribute conditions prevent source-field omission bypasses."""
from copy import deepcopy
import unittest

from agent.answer_requirements import check, inspect, parse, KEY
from agent.answer_projection import catalog
from checker.catalog import ROLES

SOURCE_ROLE = 'app.execution.source_type'
PATH_ROLE = 'app.execution.path'


def native_field(role, value):
    return {'semantic_type': ROLES[role].semantic_type, 'value': value}


def requirement(role=SOURCE_ROLE, values=None):
    return {'semantic_types': [ROLES[PATH_ROLE].semantic_type], 'meaning': 'Reviewed execution-artifact path.',
            'evidence_needed': 'The same atomic part must carry the approved source family.',
            'attribute_conditions': [{'role': role, 'values': ['Prefetch', 'UserAssist'] if values is None else values}]}


class AnswerAttributeConditions(unittest.TestCase):
    def evaluate(self, fields, raw=None):
        return check(raw or requirement(), 'attributeTuple', 'value_0', ROLES[PATH_ROLE].semantic_type,
                     part_fields=fields)

    def test_family_condition_passes_with_one_exact_typed_field_without_binding_source_leaf(self):
        fields = {'value_0': native_field(PATH_ROLE, 'C:\\Apps\\tool.exe'),
                  'value_1': native_field(SOURCE_ROLE, 'UserAssist')}
        original = deepcopy(fields)
        result = self.evaluate(fields)
        self.assertEqual(result['status'], 'compatible')
        self.assertEqual(result['condition_checks'][0]['matching_fields'], ['value_1'])
        self.assertEqual(fields, original)

    def test_omitted_or_rejected_source_cannot_license_an_execution_path(self):
        for fields, status in [({}, 'missing'),
                ({'value_0': native_field(PATH_ROLE, 'C:\\Apps\\tool.exe')}, 'missing'),
                ({'value_1': native_field(SOURCE_ROLE, 'Security process creation')}, 'incompatible'),
                ({'source': {'semantic_type': 'recorded_attribute_source_path_string', 'value': 'Prefetch'}}, 'missing')]:
            result = self.evaluate(fields)
            self.assertEqual(result['status'], 'incompatible')
            self.assertEqual(result['reason'], 'claim_attributes_do_not_meet_public_requirement')
            self.assertEqual(result['condition_checks'][0]['status'], status)
        self.assertEqual(self.evaluate(None)['status'], 'incompatible')

    def test_foreign_both_part_and_provenance_are_not_visible(self):
        current = {'value_0': native_field(PATH_ROLE, 'C:\\Apps\\tool.exe')}
        foreign = {'value_0': native_field(SOURCE_ROLE, 'UserAssist')}
        self.assertEqual(self.evaluate(current)['status'], 'incompatible')
        self.assertEqual(self.evaluate(foreign)['status'], 'compatible')
        current['value_0']['provenance'] = foreign
        current['value_0']['candidate_metadata'] = {'source': 'UserAssist'}
        self.assertEqual(self.evaluate(current)['status'], 'incompatible')

    def test_duplicate_matching_roles_refuse_even_when_values_agree(self):
        for value in ('UserAssist', 'Prefetch'):
            fields = {'value_1': native_field(SOURCE_ROLE, 'UserAssist'),
                      'value_2': native_field(SOURCE_ROLE, value)}
            result = self.evaluate(fields)
            self.assertEqual(result['status'], 'incompatible')
            self.assertEqual(result['condition_checks'][0]['status'], 'ambiguous')

    def test_exact_native_types_do_not_equate_boolean_and_integer(self):
        for role, allowed, wrong in [('scanner.detections_found', [True], 1),
                                      ('account.logon_count', [1], True)]:
            self.assertEqual(self.evaluate({'value_1': native_field(role, allowed[0])}, requirement(role, allowed))['status'], 'compatible')
            self.assertEqual(self.evaluate({'value_1': native_field(role, wrong)}, requirement(role, allowed))['status'], 'incompatible')
        self.assertEqual(self.evaluate({'value_1': native_field(SOURCE_ROLE, 'userassist')})['status'], 'incompatible')

    def test_all_conditions_and_usual_role_compatibility_are_required(self):
        raw = requirement()
        raw['attribute_conditions'].append({'role': 'account.enabled', 'values': [True]})
        fields = {'value_1': native_field(SOURCE_ROLE, 'UserAssist')}
        self.assertEqual(self.evaluate(fields, raw)['status'], 'incompatible')
        fields['value_2'] = native_field('account.enabled', True)
        self.assertEqual(self.evaluate(fields, raw)['status'], 'compatible')
        self.assertEqual(check(raw, 'attributeTuple', 'value_0', 'program', part_fields=fields)['status'], 'incompatible')

    def test_bad_configuration_is_invalid_in_parse_and_preflight(self):
        bad_conditions = [None, [], [{}], [{'role': 'unknown', 'values': ['UserAssist']}],
            [{'role': SOURCE_ROLE, 'values': []}], [{'role': SOURCE_ROLE, 'values': ['x'] * 33}],
            [{'role': SOURCE_ROLE, 'values': ['x' * 2001]}], [{'role': SOURCE_ROLE, 'values': [1]}],
            [{'role': 'account.logon_count', 'values': [True]}],
            [{'role': 'account.logon_count', 'values': [-1]}],
            [{'role': 'scanner.detections_found', 'values': [1]}],
            [{'role': SOURCE_ROLE, 'values': ['UserAssist'], 'field': 'forged'}],
            [{'role': SOURCE_ROLE, 'values': ['UserAssist']}] * 2]
        for conditions in bad_conditions:
            raw = requirement(); raw['attribute_conditions'] = conditions
            with self.subTest(conditions=conditions):
                with self.assertRaisesRegex(ValueError, 'invalid_public_claim_requirement_attribute_conditions'):
                    parse(raw)
                view = inspect({'type': 'string', KEY: raw}, catalog()['forms'])
                self.assertEqual(view['requirements'][0]['status'], 'invalid')
        view = inspect({'type': 'string', KEY: requirement()}, catalog()['forms'])
        self.assertEqual(len(view['requirements']), 1)
        self.assertEqual(view['requirements'][0]['requirement']['attribute_conditions'], requirement()['attribute_conditions'])
