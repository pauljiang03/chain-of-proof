"""C-only freezes cannot claim comparison arms or silently change run scope."""
from copy import deepcopy
import json
import unittest

from comparison.ablation.pilot import fingerprint, validate_frozen
from tests import test_ablation_pilot


class FocusedCFreeze(unittest.TestCase):
    write = test_ablation_pilot.PilotFreeze.write
    freeze = test_ablation_pilot.PilotFreeze.freeze

    def setUp(self):
        test_ablation_pilot.PilotFreeze.setUp(self)
        public = json.loads(self.questions.read_text())
        for question in public['questions']:
            question['answer_schema'] = {'type': 'string', 'x-claim-requirement': {
                'semantic_types': ['device_serial'], 'meaning': 'Synthetic recorded identifier.',
                'evidence_needed': 'Synthetic typed fixture, not a real case answer.'},
                'x-claim-scope': {'mode': 'unscoped_observation', 'meaning': 'Synthetic freeze fixture only.'}}
        self.questions.write_text(json.dumps(public))

    def focused(self, **changes):
        return self.freeze(study='focused-C', protocol='claim-bindings-v3', seconds=300, **changes)

    def test_only_one_C_call_selected_questions_and_no_causal_comparison(self):
        result = self.focused()
        manifest = result['manifest']
        self.assertEqual(manifest['study'], 'focused-C')
        self.assertEqual(manifest['order'], ['C'])
        self.assertEqual(set(manifest['arms']), {'C'})
        self.assertEqual(manifest['case']['question_ids'], ['Q1', 'Q2'])
        self.assertEqual(manifest['case']['questions'], 2)
        self.assertEqual(manifest['budget']['wall_seconds_per_live_arm'], 300)
        self.assertEqual(manifest['budget']['max_live_model_calls'], 1)
        self.assertIn('fresh investigator dispatch', manifest['budget']['model_call_unit'])
        self.assertNotIn('B_model_calls', manifest['budget'])
        self.assertNotIn('claim_filtering', manifest['measurements'])
        self.assertEqual(manifest['measurements']['comparison'], 'not_performed')
        self.assertIn('no causal comparison', manifest['measurements']['claims_allowed'])
        self.assertIn('checkpoint', manifest['measurements']['binding_policy'])
        self.assertNotIn('private value', json.dumps(manifest))
        self.assertEqual(validate_frozen(self.root/'pilot/frozen-manifest.json',
                         expected_sha256=result['manifest_sha256']), manifest)

    def test_keyless_focused_run_is_explicitly_unscored(self):
        result = self.focused(reference=None)
        manifest = result['manifest']
        self.assertEqual(manifest['evaluation_use'], 'workflow_smoke_no_accuracy_key')
        self.assertIsNone(manifest['case']['provisionally_scorable'])
        self.assertIn('unavailable_no_key', manifest['measurements']['answer_accuracy'])
        validate_frozen(self.root/'pilot/frozen-manifest.json', expected_sha256=result['manifest_sha256'])

    def test_default_study_remains_the_legacy_comparison(self):
        manifest = self.freeze()['manifest']
        self.assertNotIn('study', manifest)
        self.assertEqual(manifest['order'], ['A', 'C', 'B'])
        self.assertEqual(set(manifest['arms']), {'A', 'B', 'C'})
        self.assertEqual(manifest['budget']['wall_seconds_per_live_arm'], 900)
        self.assertNotIn('max_live_model_calls', manifest['budget'])

    def test_focused_requires_v3_explicit_bounded_budget_before_writing(self):
        for protocol, seconds in [('literal-v1', 300), ('claim-bindings-v2', 300),
                                  ('claim-bindings-v3', 301), ('claim-bindings-v3', 900),
                                  ('claim-bindings-v3', True), ('claim-bindings-v3', 0)]:
            with self.subTest(protocol=protocol, seconds=seconds), self.assertRaises(ValueError):
                self.freeze(study='focused-C', protocol=protocol, seconds=seconds)
            self.assertFalse((self.root/'pilot').exists())
        with self.assertRaisesRegex(ValueError, 'Unsupported pilot study'):
            self.freeze(study='other')

    def test_rehashed_manifest_still_cannot_add_arms_calls_or_change_scope(self):
        result = self.focused()
        path = self.root/'pilot/frozen-manifest.json'
        changes = [('order', ['A', 'C']), ('arms', {'C': 'checker', 'B': 'extra'}),
                   ('arms', ['C']), ('study', 'matched-A-C'), ('runtime_protocol', 'claim-bindings-v2'),
                   ('replicates', 2), ('replicates', True)]
        for key, value in changes:
            manifest = deepcopy(result['manifest']); manifest[key] = value
            path.write_text(json.dumps(manifest))
            with self.subTest(key=key, value=value), self.assertRaisesRegex(ValueError, 'focused-C'):
                validate_frozen(path, expected_sha256=fingerprint(path)['sha256'])
        for key, value in [('wall_seconds_per_live_arm', 301), ('wall_seconds_per_live_arm', True),
                           ('max_live_model_calls', 2), ('max_live_model_calls', True),
                           ('model_call_unit', 'provider inference request'),
                           ('B_model_calls', 0), ('extra_budget_after_failure', True)]:
            manifest = deepcopy(result['manifest']); manifest['budget'][key] = value
            path.write_text(json.dumps(manifest))
            with self.subTest(key=key, value=value), self.assertRaisesRegex(ValueError, 'focused-C'):
                validate_frozen(path, expected_sha256=fingerprint(path)['sha256'])
        for key, value in [('question_ids', ['Q2', 'Q1']), ('questions', 1), ('case_id', 'other')]:
            manifest = deepcopy(result['manifest']); manifest['case'][key] = value
            path.write_text(json.dumps(manifest))
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'selection differs'):
                validate_frozen(path, expected_sha256=fingerprint(path)['sha256'])

    def test_rehashed_model_or_claim_change_is_rejected(self):
        result = self.focused(); path = self.root/'pilot/frozen-manifest.json'
        for section, key, value in [('model', 'requested_override', 'other-model'),
                                    ('model', 'fresh_context', 'inherited'),
                                    ('measurements', 'comparison', 'causal_effect'),
                                    ('measurements', 'claims_allowed', 'universal precision')]:
            manifest = deepcopy(result['manifest']); manifest[section][key] = value
            path.write_text(json.dumps(manifest))
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'focused-C'):
                validate_frozen(path, expected_sha256=fingerprint(path)['sha256'])

    def test_changed_input_and_existing_output_are_not_repaired(self):
        result = self.focused(); path = self.root/'pilot/frozen-manifest.json'
        manifest_bytes = path.read_bytes()
        self.questions.write_bytes(self.questions.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError, 'input changed'):
            validate_frozen(path, expected_sha256=result['manifest_sha256'])
        with self.assertRaises(FileExistsError):
            self.focused()
        self.assertEqual(path.read_bytes(), manifest_bytes)


if __name__ == '__main__':
    unittest.main()
