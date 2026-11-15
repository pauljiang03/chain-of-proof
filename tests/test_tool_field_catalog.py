"""Tool metadata stays complete while sharing repeated typed-role definitions."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from agent.answer_projection import catalog, tool_catalog
from agent.answer_requirements import inspect
from agent.answer_store import answer
from agent.investigation import Investigation
from comparison.ablation.mcp_server import make_workbench
from tests.test_answer_store import public

ROOT = Path(__file__).resolve().parents[1]


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

    def test_a_and_c_receive_identical_bounded_v3_views(self):
        with tempfile.TemporaryDirectory() as directory:
            outputs = []
            for arm in ('A', 'C'):
                bench = make_workbench(arm, ROOT / 'fixtures/sample_facts.json',
                                       Path(directory) / arm, protocol='claim-bindings-v3')
                try:
                    outputs.append(bench.forms())
                finally:
                    bench._db.close()
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(outputs[0]['view'], 'static_form_catalog_page')
            self.assertEqual(outputs[0]['section'], 'claim_forms')
            self.assertLessEqual(len(json.dumps(outputs[0]).encode()), 64000)
            self.assertEqual(set(outputs[0]['form_names']['answer_fields']), set(tool_catalog()['forms']))


if __name__ == '__main__':
    unittest.main()
