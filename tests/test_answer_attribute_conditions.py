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


class NegativeAttributeConditions(unittest.TestCase):
    def requirement(self, excluded=None, comparison='casefold'):
        raw = requirement()
        raw['attribute_conditions'] = [{
            'role': 'account.name',
            'excluded_values': ['Administrator', 'Guest', 'systemprofile', 'LocalService', 'NetworkService']
                               if excluded is None else excluded,
            'string_comparison': comparison}]
        return raw

    def evaluate(self, value=None, *, fields=None, raw=None):
        if fields is None:
            fields = {'value_1': native_field('account.name', value)}
        return check(raw or self.requirement(), 'attributeTuple', 'value_0',
                     ROLES[PATH_ROLE].semantic_type, part_fields=fields)

    def test_casefold_excludes_entire_names_and_preserves_diagnostics(self):
        for value in ('Administrator', 'ADMINISTRATOR', 'guest', 'SYSTEMPROFILE',
                      'localservice', 'NetworkService'):
            with self.subTest(value=value):
                fields = {'value_1': native_field('account.name', value)}
                before = deepcopy(fields)
                result = self.evaluate(fields=fields)
                self.assertEqual(result['status'], 'incompatible')
                diagnostic = result['condition_checks'][0]
                self.assertEqual(diagnostic['string_comparison'], 'casefold')
                self.assertEqual(diagnostic['excluded_values'], self.requirement()['attribute_conditions'][0]['excluded_values'])
                self.assertEqual(diagnostic['offered_value'], value)
                self.assertNotIn('values', diagnostic)
                self.assertEqual(fields, before)
        for value in ('SyntheticUser', 'Administrator2', 'DOMAIN\\Administrator',
                      ' Administrator', 'Administrator ', '.*', ''):
            with self.subTest(value=value):
                self.assertEqual(self.evaluate(value)['status'], 'compatible')

    def test_exact_and_casefold_are_explicit_without_regex_trim_or_normalization(self):
        exact = self.requirement(['Guest'], 'exact')
        self.assertEqual(self.evaluate('Guest', raw=exact)['status'], 'incompatible')
        self.assertEqual(self.evaluate('guest', raw=exact)['status'], 'compatible')
        self.assertEqual(self.evaluate('Straße', raw=self.requirement(['STRASSE']))['status'], 'incompatible')
        self.assertEqual(self.evaluate('e\u0301', raw=self.requirement(['é']))['status'], 'compatible')
        for excluded, value in [(['Admin.*'], 'Administrator'), (['Admin'], 'Administrator'),
                                (['Guest'], ' Guest '), (['[A-Z]'], 'X')]:
            self.assertEqual(self.evaluate(value, raw=self.requirement(excluded))['status'], 'compatible')
        self.assertEqual(self.evaluate('', raw=self.requirement(['']))['status'], 'incompatible')
        self.assertEqual(self.evaluate(' ', raw=self.requirement(['']))['status'], 'compatible')

    def test_missing_ambiguous_wrong_semantic_or_native_values_never_pass_negative(self):
        cases = [({}, 'missing'),
                 ({'value_1': native_field(SOURCE_ROLE, 'UserAssist')}, 'missing'),
                 ({'value_1': native_field('account.name', 'SyntheticUser'),
                   'value_2': native_field('account.name', 'SyntheticUser')}, 'ambiguous')]
        for fields, status in cases:
            result = self.evaluate(fields=fields)
            self.assertEqual(result['status'], 'incompatible')
            diagnostic = result['condition_checks'][0]
            self.assertEqual(diagnostic['status'], status)
            self.assertNotIn('offered_value', diagnostic)
            self.assertIn('excluded_values', diagnostic)
            self.assertEqual(diagnostic['string_comparison'], 'casefold')
        for value in (None, False, True, 0, -1, 1.0, [], {}, 'x' * 2001):
            with self.subTest(value=value):
                self.assertEqual(self.evaluate(value)['status'], 'incompatible')
        missing_value = {'value_1': {'semantic_type': ROLES['account.name'].semantic_type}}
        self.assertEqual(self.evaluate(fields=missing_value)['status'], 'incompatible')
        raw = self.requirement()
        result = check(raw, 'attributeTuple', 'value_0', ROLES[PATH_ROLE].semantic_type)
        self.assertEqual(result['condition_checks'][0]['status'], 'missing')

    def test_other_part_provenance_and_metadata_cannot_fill_required_name(self):
        current = {'value_0': native_field(PATH_ROLE, 'C:\\Synthetic\\tool.exe')}
        foreign = {'value_1': native_field('account.name', 'SyntheticUser')}
        current['value_0']['provenance'] = foreign
        current['value_0']['candidate_metadata'] = {'account.name': 'SyntheticUser'}
        self.assertEqual(self.evaluate(fields=current)['status'], 'incompatible')
        self.assertEqual(self.evaluate(fields=foreign)['status'], 'compatible')

    def test_positive_schema_and_exact_native_comparison_are_unchanged(self):
        raw = requirement('account.name', ['Guest'])
        self.assertEqual(self.evaluate('Guest', raw=raw)['status'], 'compatible')
        self.assertEqual(self.evaluate('guest', raw=raw)['status'], 'incompatible')
        result = self.evaluate('Guest', raw=raw)
        self.assertEqual(result['condition_checks'][0]['values'], ['Guest'])
        self.assertNotIn('excluded_values', result['condition_checks'][0])
        self.assertNotIn('string_comparison', result['condition_checks'][0])
        self.assertEqual(parse(raw), raw)

    def test_bad_negative_shapes_and_types_are_invalid_in_parse_and_inspect(self):
        good = self.requirement()['attribute_conditions'][0]
        bad = [dict(role='account.name', excluded_values=['Guest']),
               dict(good, values=['User']), dict(good, string_comparison='substring'),
               dict(good, string_comparison='regex'), dict(good, string_comparison=None),
               dict(good, string_comparison=[]), dict(good, extra=True),
               dict(good, role='unknown.role'), dict(good, role='account.logon_count'),
               dict(good, role='scanner.detections_found'), dict(good, excluded_values=[]),
               dict(good, excluded_values=['x'] * 33), dict(good, excluded_values=['x' * 2001]),
               dict(role='account.name', values=['Guest'], string_comparison='exact')]
        bad.extend(dict(good, excluded_values=[value]) for value in (None, 0, True, 1.0, [], {}))
        for condition in bad:
            raw = self.requirement(); raw['attribute_conditions'] = [condition]
            with self.subTest(condition=condition):
                with self.assertRaisesRegex(ValueError, 'invalid_public_claim_requirement_attribute_conditions'):
                    parse(raw)
                view = inspect({'type': 'string', KEY: raw}, catalog()['forms'])
                self.assertEqual(view['requirements'][0]['status'], 'invalid')
        raw = self.requirement()
        raw['attribute_conditions'].append({'role': 'account.name', 'values': ['SyntheticUser']})
        with self.assertRaises(ValueError):
            parse(raw)

    def test_signed_native_literals_and_positive_conditions_preserve_unsigned_policy(self):
        from unittest.mock import patch
        from checker.catalog import AttributeRole
        from agent.answer_requirements import _native_literal
        signed = next((role for role in ROLES.values() if role.value_type == 'signed_integer'), None)
        if signed is None:
            signed = AttributeRole('synthetic.signed', 'roleSyntheticSigned', 'signed_integer',
                                   'Synthetic signed source value for literal-type validation.')
        with patch.dict(ROLES, {signed.name: signed}):
            raw = requirement(signed.name, [-60, 0, 60])
            self.assertEqual(parse(raw), raw)
            for value in (-60, 0, 60):
                self.assertTrue(_native_literal(value, 'signed_integer'))
                self.assertEqual(self.evaluate(fields={'signed': native_field(signed.name, value)}, raw=raw)['status'], 'compatible')
            for value in (True, False, -60.0, '-60', None, [], {}):
                self.assertFalse(_native_literal(value, 'signed_integer'))
                self.assertEqual(self.evaluate(fields={'signed': native_field(signed.name, value)}, raw=raw)['status'], 'incompatible')
                invalid = requirement(signed.name, [value])
                with self.assertRaises(ValueError):
                    parse(invalid)
            self.assertFalse(_native_literal(-60, 'integer'))
            self.assertTrue(_native_literal(60, 'integer'))
            self.assertFalse(_native_literal(True, 'integer'))
            negative_signed = self.requirement()
            negative_signed['attribute_conditions'][0]['role'] = signed.name
            with self.assertRaises(ValueError):
                parse(negative_signed)
