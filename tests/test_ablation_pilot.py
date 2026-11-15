"""Freeze the exact pilot inputs and distinguish unsupported measurements."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from comparison.ablation.pilot import fingerprint, freeze_pilot, validate_frozen


class PilotFreeze(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.facts = self.write("facts.json", {"facts": []})
        self.profile = self.write("profile.json", {"name": "Public case", "brief": "Public context",
            "case_id": "case", "questions": ["What is recorded?"]})
        self.questions = self.write("questions.json", {"schema_version": 2, "case_id": "case",
            "questions": [{"id": "Q1", "prompt": "What is recorded?", "answer_schema": {}},
                          {"id": "Q2", "prompt": "What remains unknown?", "answer_schema": {}}]})
        self.reference = self.write("reference.json", {"schema_version": 2, "case_id": "case",
            "questions": [{"id": "Q1", "prompt": "What is recorded?", "expected": "private value"},
                          {"id": "Q2", "prompt": "What remains unknown?", "evaluation": {
                              "status": "unevaluable", "reason": "Unresolved before execution"}}]})

    def write(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value))
        return path

    def freeze(self, **changes):
        arguments = dict(facts=self.facts, case_profile=self.profile, questions=self.questions,
                         reference=self.reference, out=self.root / "pilot", seconds=900)
        arguments.update(changes)
        return freeze_pilot(**arguments)

    def test_frozen_inputs_unknown_model_usage_and_distinct_metrics(self):
        result = self.freeze()
        manifest = result["manifest"]
        self.assertEqual(manifest["order"], ["A", "C", "B"])
        self.assertEqual(manifest["case"]["provisionally_scorable"], 1)
        self.assertEqual(manifest["case"]["unevaluable_ids"], ["Q2"])
        self.assertIsNone(manifest["model"]["observed_model_id"])
        self.assertIsNone(manifest["budget"]["model_tokens"])
        self.assertEqual(manifest["model"]["requested_override"], "gpt-6.1-sol")
        self.assertIn("unverified", manifest["measurements"]["answer_accuracy"])
        self.assertIn("no B question", manifest["measurements"]["shared_claim_faithful_projector"])
        self.assertNotIn("private value", json.dumps(manifest))
        self.assertEqual(validate_frozen(self.root / "pilot/frozen-manifest.json",
            expected_sha256=result["manifest_sha256"]), manifest)

    def test_changed_input_or_replaced_manifest_fails_retained_checkpoint(self):
        result = self.freeze()
        path = self.root / "pilot/frozen-manifest.json"
        old = self.facts.read_bytes()
        self.facts.write_bytes(old + b" ")
        with self.assertRaisesRegex(ValueError, "input changed"):
            validate_frozen(path, expected_sha256=result["manifest_sha256"])
        self.facts.write_bytes(old)
        path.write_text(path.read_text() + " ")
        with self.assertRaisesRegex(ValueError, "checkpoint"):
            validate_frozen(path, expected_sha256=result["manifest_sha256"])

    def test_contract_conflict_and_existing_output_do_not_overwrite(self):
        public = json.loads(self.questions.read_text())
        public["questions"][0]["prompt"] = "A different question"
        self.questions.write_text(json.dumps(public))
        with self.assertRaisesRegex(ValueError, "contracts differ"):
            self.freeze()
        self.assertFalse((self.root / "pilot").exists())
        public["questions"][0]["prompt"] = "What is recorded?"
        self.questions.write_text(json.dumps(public))
        self.freeze()
        before = fingerprint(self.root / "pilot/frozen-manifest.json")
        with self.assertRaises(FileExistsError):
            self.freeze()
        self.assertEqual(before, fingerprint(self.root / "pilot/frozen-manifest.json"))

    def test_implementation_change_and_invalid_budgets_are_rejected(self):
        for seconds in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                self.freeze(seconds=seconds)
        result = self.freeze()
        changed = copy.deepcopy(result["manifest"]["software"])
        changed["source_sha256"]["agent/tools.py"] = "0" * 64
        with patch("comparison.ablation.pilot._software", return_value=changed):
            with self.assertRaisesRegex(ValueError, "implementation changed"):
                validate_frozen(self.root / "pilot/frozen-manifest.json",
                                expected_sha256=result["manifest_sha256"])


if __name__ == "__main__":
    unittest.main()
