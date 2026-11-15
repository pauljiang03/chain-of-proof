"""Temporary-fixture checks for keyless operational smoke manifests."""
import copy
import json
from unittest.mock import patch

from comparison.ablation.pilot import fingerprint, validate_frozen
from tests.test_ablation_pilot import PilotFreeze


class SmokeFreeze(PilotFreeze):
    def test_keyless_v2_is_explicitly_unscored_and_pins_only_public_inputs(self):
        result = self.freeze(protocol='claim-bindings-v2', reference=None, seconds=45)
        manifest = result['manifest']
        self.assertEqual(set(manifest['inputs']), {'facts', 'case_profile', 'questions'})
        self.assertEqual(manifest['runtime_protocol'], 'claim-bindings-v2')
        self.assertEqual(manifest['evaluation_use'], 'workflow_smoke_no_accuracy_key')
        self.assertIn('inventory_page', manifest['isolation']['allowed_reads'])
        self.assertIn('No posthoc binding inference', manifest['measurements']['binding_policy'])
        self.assertEqual(manifest['case']['reference_status'], 'unavailable_no_key')
        self.assertIsNone(manifest['case']['provisionally_scorable'])
        self.assertIsNone(manifest['case']['unevaluable_ids'])
        self.assertIn('no question accuracy', manifest['measurements']['answer_accuracy'])
        self.assertIn('whole candidates', manifest['measurements']['shared_claim_faithful_projector'])
        self.assertEqual(manifest['budget']['B_model_calls'], 0)
        self.assertEqual(manifest['budget']['wall_seconds_per_live_arm'], 45)
        self.assertEqual(validate_frozen(self.root / 'pilot/frozen-manifest.json',
            expected_sha256=result['manifest_sha256']), manifest)

    def test_legacy_requires_reference(self):
        with self.assertRaisesRegex(ValueError, 'requires a private reference'):
            self.freeze(reference=None)
        self.assertFalse((self.root / 'pilot').exists())

    def test_v2_retains_private_contract_validation(self):
        private = json.loads(self.reference.read_text())
        private['questions'][0]['match'] = {'strings': 'exact'}
        self.reference.write_text(json.dumps(private))
        with self.assertRaisesRegex(ValueError, 'contracts differ'):
            self.freeze(protocol='claim-bindings-v2')

    def test_strict_public_json_rejects_duplicate_and_nonfinite_values(self):
        for path in (self.profile, self.questions):
            original = path.read_text()
            for suffix in (',"bad":NaN}', ',"bad":1e999}', ',"case_id":"duplicate"}'):
                path.write_text(original[:-1] + suffix)
                with self.assertRaisesRegex(ValueError, 'Duplicate|Non-finite'):
                    self.freeze(protocol='claim-bindings-v2', reference=None)
            path.write_text(original)

    def test_v2_rejects_input_and_source_changes(self):
        result = self.freeze(protocol='claim-bindings-v2', reference=None)
        path = self.root / 'pilot/frozen-manifest.json'
        original = self.questions.read_bytes()
        self.questions.write_bytes(original + b' ')
        with self.assertRaisesRegex(ValueError, 'input changed'):
            validate_frozen(path, expected_sha256=result['manifest_sha256'])
        self.questions.write_bytes(original)
        changed = copy.deepcopy(result['manifest']['software'])
        changed['source_sha256']['lean/lakefile.toml'] = '0' * 64
        with patch('comparison.ablation.pilot._software', return_value=changed):
            with self.assertRaisesRegex(ValueError, 'implementation changed'):
                validate_frozen(path, expected_sha256=result['manifest_sha256'])

    def test_protocol_conditional_input_keyset_and_legacy_fallback(self):
        result = self.freeze()
        path = self.root / 'pilot/frozen-manifest.json'
        manifest = result['manifest']
        del manifest['runtime_protocol']
        path.write_text(json.dumps(manifest))
        self.assertEqual(validate_frozen(path, expected_sha256=fingerprint(path)['sha256']), manifest)
        del manifest['inputs']['reference']
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'Unsupported'):
            validate_frozen(path, expected_sha256=fingerprint(path)['sha256'])
