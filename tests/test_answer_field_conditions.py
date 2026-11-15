"""Same-part projected fields must match public extraction definitions exactly."""
from copy import deepcopy
import unittest
from agent.answer_requirements import KEY, SCOPE_KEY, parse, check, inspect, parse_scope
from agent.answer_projection import catalog
from tests.test_answer_requirements import need

DEFINITION = 'Reader definition: deleted entries within the selected extracted filesystem set.'


def requirement(values=None):
    raw = need('recorded_extracted_filesystem_count')
    raw['field_conditions'] = [{'field': 'definition', 'semantic_type': 'filesystem_set_definition',
                               'values': [DEFINITION] if values is None else values}]
    return raw


class AnswerFieldConditions(unittest.TestCase):
    def evaluate(self, fields, raw=None):
        return check(raw or requirement(), 'filesystemSetDeleted', 'count',
                     'recorded_extracted_filesystem_count', part_fields=fields)

    def test_exact_named_same_part_field_passes_without_binding_definition(self):
        fields = {'definition': {'semantic_type': 'filesystem_set_definition', 'value': DEFINITION}}
        before = deepcopy(fields)
        result = self.evaluate(fields)
        self.assertEqual(result['status'], 'compatible')
        self.assertEqual(result['field_condition_checks'][0]['status'], 'compatible')
        self.assertEqual(fields, before)

    def test_missing_wrong_field_type_value_and_provenance_refuse_without_repair(self):
        field = {'semantic_type': 'filesystem_set_definition', 'value': DEFINITION}
        for fields in (None, {}, {'other_name': field},
                       {'definition': dict(field, semantic_type='arbitrary_text')},
                       {'definition': dict(field, value=DEFINITION+' changed')},
                       {'definition': {'semantic_type': 'filesystem_set_definition'}},
                       {'provenance': {'definition': field}}):
            with self.subTest(fields=fields):
                result = self.evaluate(fields)
                self.assertEqual(result['status'], 'incompatible')
                self.assertEqual(result['reason'], 'claim_fields_do_not_meet_public_requirement')

    def test_json_boolean_integer_string_are_distinct_and_case_is_exact(self):
        for allowed, offered in ((True, 1), (1, True), ('1', 1), ('Reader', 'reader')):
            raw = requirement([allowed])
            good = {'definition': {'semantic_type': 'filesystem_set_definition', 'value': allowed}}
            self.assertEqual(self.evaluate(good, raw)['status'], 'compatible')
            good['definition']['value'] = offered
            self.assertEqual(self.evaluate(good, raw)['status'], 'incompatible')

    def test_every_condition_and_normal_leaf_role_are_required(self):
        raw = requirement()
        raw['field_conditions'].append({'field': 'second', 'semantic_type': 'boolean_flag', 'values': [True]})
        fields = {'definition': {'semantic_type': 'filesystem_set_definition', 'value': DEFINITION}}
        self.assertEqual(self.evaluate(fields, raw)['status'], 'incompatible')
        fields['second'] = {'semantic_type': 'boolean_flag', 'value': True}
        self.assertEqual(self.evaluate(fields, raw)['status'], 'compatible')
        self.assertEqual(check(raw, 'filesystemSetDeleted', 'count', 'wrong_role', part_fields=fields)['status'], 'incompatible')

    def test_unconditioned_requirement_keeps_previous_behavior(self):
        self.assertEqual(check(need('program'), 'programRan', 'program', 'program')['status'], 'compatible')

    def test_invalid_bounded_configuration_fails_parse_and_preflight(self):
        good = requirement()['field_conditions'][0]
        malformed = [None, [], [good]*9, [good]*2, [{}],
            [dict(good, field='not.a.field')], [dict(good, semantic_type='')],
            [dict(good, extra=True)], [dict(good, values=[])], [dict(good, values=['x']*33)],
            [dict(good, values=['x'*2001])]]
        malformed += [[dict(good, values=[value])] for value in (None, 1.0, -1, {}, [], float('inf'))]
        for conditions in malformed:
            raw = requirement(); raw['field_conditions'] = conditions
            with self.subTest(conditions=conditions):
                with self.assertRaisesRegex(ValueError, 'invalid_public_claim_requirement_field_conditions'):
                    parse(raw)
                view = inspect({'type': 'integer', KEY: raw}, catalog()['forms'])
                self.assertEqual(view['requirements'][0]['status'], 'invalid')

    def test_conditions_are_preserved_in_preflight_without_evidence_queries(self):
        raw = requirement()
        view = inspect({'type': 'integer', KEY: raw}, catalog()['forms'])
        self.assertEqual(view['requirements'][0]['requirement']['field_conditions'], raw['field_conditions'])
        self.assertEqual(parse(raw), raw)

    def test_required_attribute_roles_need_exactly_one_same_part_field_each(self):
        from checker.catalog import ROLES
        roles = ['recycle.index_file_name', 'recycle.original_path', 'recycle.index_deleted_at']
        raw = need('program')
        raw['required_attribute_roles'] = roles
        fields = {'value_'+str(i): {'semantic_type': ROLES[role].semantic_type, 'value': 'fixture'}
                  for i, role in enumerate(roles)}
        evaluate = lambda part: check(raw, 'attributeTuple', 'value_0', 'program', part_fields=part)
        self.assertEqual(evaluate(fields)['status'], 'compatible')
        for missing in fields:
            partial = {name: row for name, row in fields.items() if name != missing}
            result = evaluate(partial)
            self.assertEqual(result['status'], 'incompatible')
            self.assertEqual(result['reason'], 'claim_attributes_do_not_meet_public_requirement')
        duplicated = dict(fields, duplicate=fields['value_0'])
        self.assertEqual(evaluate(duplicated)['required_attribute_role_checks'][0]['status'], 'ambiguous')
        current_part = {'value_1': fields['value_1']}
        current_part['foreign_part'] = {'fields': fields}
        self.assertEqual(evaluate(current_part)['status'], 'incompatible')
        self.assertEqual(evaluate(None)['status'], 'incompatible')
        self.assertEqual(parse(raw)['required_attribute_roles'], roles)
        view = inspect({'type': 'string', KEY: raw}, catalog()['forms'])
        self.assertEqual(view['requirements'][0]['requirement']['required_attribute_roles'], roles)

    def test_required_attribute_roles_configuration_is_bounded_and_reviewed(self):
        roles = ['recycle.index_file_name', 'recycle.original_path', 'recycle.index_deleted_at']
        for invalid in (None, [], roles*3, ['recycle.original_path']*2, ['not.approved'], [1], [{}]):
            raw = need('program'); raw['required_attribute_roles'] = invalid
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(ValueError, 'invalid_public_claim_requirement_required_attribute_roles'):
                    parse(raw)
                view = inspect({'type': 'string', KEY: raw}, catalog()['forms'])
                self.assertEqual(view['requirements'][0]['status'], 'invalid')

    def test_same_origin_flag_is_explicit_boolean_only(self):
        origin = {'image': 'fixture.E01', 'exhibit': 'PC', 'source_snapshot': 'base-volume', 'source_variant': 'primary'}
        base = {'mode': 'source_records', 'origins': [origin]}
        for value in (True, False):
            raw = dict(base, same_origin=value)
            self.assertEqual(parse_scope(raw), raw)
        self.assertEqual(parse_scope(base), base)
        for value in (None, 1, 0, 'true', [], {}):
            raw = dict(base, same_origin=value)
            with self.assertRaisesRegex(ValueError, 'invalid_public_claim_scope_requirement'):
                parse_scope(raw)
            view = inspect({'type': 'integer', SCOPE_KEY: raw}, catalog()['forms'])
            self.assertTrue(any(row['status'] == 'invalid' for row in view['requirements']))
        with self.assertRaises(ValueError):
            parse_scope({'mode': 'unscoped_observation', 'meaning': 'Fixture only.', 'same_origin': True})


if __name__ == '__main__':
    unittest.main()
