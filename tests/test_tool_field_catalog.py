"""Tool metadata stays complete while sharing repeated typed-role definitions."""
from copy import deepcopy
import json
import tempfile
import unittest

from agent.answer_projection import catalog, tool_catalog
from agent.answer_requirements import inspect
from agent.answer_store import answer
from agent.investigation import Investigation
from tests.test_answer_store import public


class ToolFieldCatalog(unittest.TestCase):
    def test_shared_references_preserve_every_form_selector_role_and_type(self):
        full, compact = catalog(), tool_catalog()
        expanded = deepcopy(compact['forms'])
        references = 0
        for fields in expanded.values():
            for selector in fields.values():
                if 'allowed_semantic_types_ref' in selector:
                    self.assertEqual(selector.pop('allowed_semantic_types_ref'), '#/attribute_roles')
                    selector['allowed_semantic_types'] = [role['semantic_type']
                        for role in compact['attribute_roles'].values()]
                    references += 1
        self.assertGreaterEqual(references, 8)
        self.assertEqual(expanded, full['forms'])
        for key in full:
            if key != 'forms':
                self.assertEqual(compact[key], full[key])
        self.assertIn('tuple_entry', compact['attribute_type_lookup'])
        compact['attribute_roles'].clear()
        compact['forms']['attributeTuple'].clear()
        self.assertEqual(catalog(), full)

    def test_tool_payload_is_substantially_smaller(self):
        full_size = len(json.dumps(catalog()).encode())
        compact_size = len(json.dumps(tool_catalog()).encode())
        self.assertLess(compact_size, full_size * 0.6)

    def test_native_inspection_uses_compact_view_and_full_internal_preflight(self):
        profile = public()
        with tempfile.TemporaryDirectory() as directory:
            Investigation(directory).initialize(profile)
            result = answer(directory, 'DEVICES')
        self.assertEqual(result['field_catalog'], tool_catalog())
        expected = inspect(profile['questions'][0]['answer_schema'], catalog()['forms'],
                           require_claim_requirements=True, require_evidence_scope=True)
        self.assertEqual(result['field_requirements'], expected)


if __name__ == '__main__':
    unittest.main()
