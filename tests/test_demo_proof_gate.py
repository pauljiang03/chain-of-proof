"""The proof-gate demo must exercise the real checker and independent verifier."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import demo_proof_gate as demo


class ProofGateDemo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.directory = Path(cls.temporary.name) / "demo"
        cls.original_fixture = demo.FIXTURE.read_bytes()
        cls.result = demo.run_demo(cls.directory)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_real_kernel_and_independent_verification_accept_the_valid_claim(self):
        self.assertTrue(self.result["passed"])
        self.assertEqual(self.result["valid_claim"]["status"], "verified")
        self.assertEqual(self.result["valid_claim"]["trust_tier"], "kernel")
        self.assertEqual(self.result["valid_claim"]["axioms"], [])
        self.assertEqual(self.result["independent_verification"], {"passed": True, "problems": []})
        self.assertTrue((self.directory / "certificates/DemoValid.lean").is_file())

    def test_wrong_device_is_refused_for_the_actual_failed_identity_equality(self):
        invalid = self.result["invalid_claim"]
        self.assertEqual(invalid["status"], "rejected")
        self.assertEqual(invalid["failing_conditions"], ["FAIL link 4600 (aux) 4511 (aux)"])
        self.assertFalse(invalid["identity_condition"]["equal"])
        self.assertNotEqual(invalid["identity_condition"]["file_open_volume"],
                            invalid["identity_condition"]["mounted_volume"])
        self.assertFalse((self.directory / "certificates/DemoWrongDevice.json").exists())
        self.assertFalse((self.directory / "certificates/DemoWrongDevice.lean").exists())

    def test_tampered_copied_value_is_refused_even_with_the_original_hash(self):
        original = json.loads((self.directory / "certificates/DemoValid.json").read_text())
        altered = json.loads((self.directory / "tampered-certificate.json").read_text())
        before = next(row for row in original["cited_facts"] if row["id"] == 4600)
        after = next(row for row in altered["cited_facts"] if row["id"] == 4600)
        self.assertEqual(before["row_sha256"], after["row_sha256"])
        self.assertNotEqual(before["aux_text"], after["aux_text"])
        self.assertEqual(self.result["tamper"]["problems"], ["fact 4600 copied fields differ from the evidence DB"])

    def test_fixture_is_unchanged_and_output_is_explicitly_synthetic(self):
        self.assertEqual(demo.FIXTURE.read_bytes(), self.original_fixture)
        self.assertEqual((self.directory / "facts.json").read_bytes(), self.original_fixture)
        self.assertEqual(self.result["fixture"]["sha256"], hashlib.sha256(self.original_fixture).hexdigest())
        self.assertEqual(json.loads((self.directory / "result.json").read_text()), self.result)
        text = demo.render(self.result)
        self.assertIn("SYNTHETIC", text)
        self.assertIn("no AI or benchmark score", text)
        self.assertIn(r"E:\sample\design_concept.ppt", text)
        self.assertIn("SAMPLE-VOL-RM2 != SAMPLE-VOL-RM1", text)
        self.assertIn("does not prove", text)

    def test_existing_output_and_symlink_are_refused_before_checking(self):
        before = (self.directory / "result.json").read_bytes()
        with patch.object(demo, "check") as check:
            with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
                demo.run_demo(self.directory)
            dangling = Path(self.temporary.name) / "dangling"
            dangling.symlink_to(Path(self.temporary.name) / "absent")
            with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
                demo.run_demo(dangling)
            check.assert_not_called()
        self.assertEqual((self.directory / "result.json").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
