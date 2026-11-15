"""Selector growth follows centrally approved roles, never arbitrary variants."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from agent import answer_projection, answer_requirements, answer_views
from checker.catalog import AttributeRole, ROLES


class CatalogRoleGrowth(unittest.TestCase):
    def setUp(self):
        approved = dict(ROLES)
        for i in range(max(180 - len(approved), 1)):
            name = 'growth.field_' + str(i).zfill(3)
            approved[name] = AttributeRole(name, 'roleSyntheticGrowth' + str(i), 'string',
                                          'Synthetic centrally approved role for deterministic catalog growth checks. '
                                          'This typed source observation does not establish execution, physical user, '
                                          'authenticity, action, complete coverage or personal attribution.')
        self.approved = approved
        self.variants = [role.semantic_type for role in approved.values()]
        self.assertGreaterEqual(len(self.variants), 180)
        fields = deepcopy(answer_projection._FIELDS)
        for form in fields.values():
            for selector in form.values():
                if 'value_role_argument' in selector:
                    selector['allowed_semantic_types'] = list(self.variants)
        self.patchers = [patch.dict(ROLES, approved, clear=True),
                         patch.object(answer_projection, '_FIELDS', fields)]
        for patcher in self.patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def schema(self):
        return {'type': 'string', 'x-claim-requirement': {
            'semantic_types': [self.variants[-1]],
            'selectors': [{'form': 'attributeTuple', 'field': 'value_7'}],
            'meaning': 'Exact centrally approved growth role.',
            'evidence_needed': 'A typed source value with this fixed role.'}}

    def test_over_128_approved_variants_survive_catalog_and_inspect(self):
        full = answer_projection.catalog()
        self.assertEqual(len(full['attribute_roles']), len(self.approved))
        selector = full['forms']['attributeTuple']['value_7']
        self.assertEqual(answer_requirements._semantic_types(selector), self.variants)
        result = answer_requirements.inspect(self.schema(), full['forms'], require_claim_requirements=True)
        row, = result['requirements']
        self.assertEqual(row['status'], 'catalog_support')
        self.assertEqual(row['available_fields'], [{'form': 'attributeTuple', 'field': 'value_7',
                                                  'semantic_type': self.variants[-1]}])

    def test_unknown_duplicate_oversized_and_malformed_variants_are_refused(self):
        for variants in ([self.variants[0], 'recorded_attribute_not_centrally_approved_string'],
                         [self.variants[0], self.variants[0]],
                         self.variants + [self.variants[0]], [],
                         [self.variants[0], []], ['invalid-name'], 'not a list'):
            with self.subTest(variants=variants):
                with self.assertRaisesRegex(ValueError, 'invalid_catalog_semantic_type_variants'):
                    answer_requirements._semantic_types({'allowed_semantic_types': variants})
        forms = {'Synthetic': {'value': {'semantic_type': 'narrow',
                 'allowed_semantic_types': ['recorded_attribute_unapproved_string']}}}
        result = answer_requirements.inspect(self.schema(), forms, require_claim_requirements=True)
        self.assertEqual(result['requirements'][0]['status'], 'invalid')
        self.assertEqual(result['requirements'][0]['reason'], 'invalid_catalog_semantic_type_variants')

    def test_no_variant_selector_behavior_is_unchanged(self):
        self.assertEqual(answer_requirements._semantic_types({'semantic_type': 'ordinary_fixed_role'}),
                         ['ordinary_fixed_role'])
        self.assertEqual(answer_requirements._semantic_types({'semantic_type': 'ordinary_fixed_role',
                                                              'allowed_semantic_types': None}),
                         ['ordinary_fixed_role'])
        with self.assertRaises(KeyError):
            answer_requirements._semantic_types({})

    def test_compact_tool_catalog_json_roundtrip_recovers_all_selectors_and_roles(self):
        full = answer_projection.catalog()
        compact = json.loads(json.dumps(answer_projection.tool_catalog()))
        self.assertEqual(compact['attribute_roles'], full['attribute_roles'])
        shared = [spec['semantic_type'] for spec in compact['attribute_roles'].values()]
        references = 0
        for fields in compact['forms'].values():
            for selector in fields.values():
                if 'allowed_semantic_types_ref' in selector:
                    self.assertEqual(selector.pop('allowed_semantic_types_ref'), '#/attribute_roles')
                    selector['allowed_semantic_types'] = shared
                    references += 1
        self.assertGreater(references, 8)
        compact.pop('view')
        compact.pop('attribute_type_lookup')
        self.assertEqual(compact, full)

    def test_native_catalog_pages_stay_under_64k_and_discover_every_role_and_form(self):
        catalog = answer_projection.tool_catalog()
        metadata = {'question_id': 'Q', 'bindings': [], 'field_catalog': catalog,
                    'field_requirements': answer_requirements.inspect(
                        self.schema(), answer_projection.catalog()['forms'], require_claim_requirements=True)}
        snapshot = {'inspection': metadata, 'projection': None}
        rows, offset, token = [], 0, None
        with patch('agent.answer_store._inspection_snapshot', return_value=snapshot):
            while True:
                result = answer_views.inspection('unused', 'Q', section='field_catalog', offset=offset,
                                                 page_size=100, state_token=token)
                self.assertLess(len(json.dumps(result, ensure_ascii=True).encode()), 64_000)
                rows.extend(result['field_catalog'])
                token = result['state_token']
                offset = result['page']['next_offset']
                if offset is None:
                    self.assertEqual(len(rows), result['page']['total'])
                    break
        self.assertFalse(any(row.get('view') == 'omitted_oversize_value' for row in rows))
        roles = {row['path'][1] for row in rows if row['path'][0] == 'attribute_roles'}
        forms = {row['path'][1] for row in rows if row['path'][0] == 'forms'}
        self.assertEqual(roles, set(self.approved))
        self.assertEqual(forms, set(catalog['forms']))


if __name__ == '__main__':
    unittest.main()
