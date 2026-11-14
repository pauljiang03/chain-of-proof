"""Rejection guidance describes source-backed failures without becoming a proof."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from checker import claims, needs
from checker import check as checker
from checker.facts import JsonFacts
from verifier.verify import verify


ROOT = Path(__file__).resolve().parent.parent


class ProofNeeds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = JsonFacts(ROOT / "fixtures" / "sample_facts.json")

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.out = Path(self.directory.name)

    def check(self, claim, name="Needs"):
        result = checker.check(claim, name, self.source, out_dir=self.out)
        if result["status"] == "rejected":
            gap = result["proof_gap"]
            self.assertEqual(gap["status"], "diagnostic")
            self.assertTrue(gap["requirements"])
            self.assertIn("not a certificate", gap["disclaimer"])
            self.assertIn("may not exist", gap["disclaimer"])
            self.assertFalse((self.out / (name + ".lean")).exists())
            self.assertFalse((self.out / (name + ".json")).exists())
            logged = json.loads((self.out / "proposals.jsonl").read_text().splitlines()[-1])
            self.assertEqual(logged["proof_gap"], gap)
        return result

    def test_unknown_record_requires_source_lookup_not_invented_ids_or_kernel_work(self):
        with patch.object(checker, "run_kernel") as kernel, patch.object(checker, "explain") as explain:
            result = self.check({"before": [4512, 999999]})
        kernel.assert_not_called()
        explain.assert_not_called()
        gap = result["proof_gap"]["requirements"][0]
        self.assertEqual(gap["category"], "missing_record")
        self.assertEqual(gap["fact_ids"], [999999])
        self.assertEqual(gap["observed"]["present_fact_ids"], [4512])
        self.assertIn("Do not invent IDs", gap["action"])

    def test_conflicting_serials_are_existing_conflict_not_missing_evidence(self):
        before = {f.id: f.row_sha256() for f in self.source.all()}
        with patch.object(checker, "run_kernel", wraps=checker.run_kernel) as kernel, \
             patch.object(checker, "explain", wraps=checker.explain) as explain:
            result = self.check({"usbMountedAs": [4512, 4511]})
        self.assertEqual(kernel.call_count, 1)
        self.assertEqual(explain.call_count, 1)
        gaps = result["proof_gap"]["requirements"]
        self.assertEqual([g["category"] for g in gaps], ["contradictory_identity_or_value"])
        gap = gaps[0]
        self.assertEqual(gap["fact_ids"], [4512, 4511])
        self.assertIn("conflict", gap["reason"])
        self.assertIn("do not rewrite", gap["action"])
        self.assertEqual(gap["required"]["rules"], ["R1", "R2"])
        records = gap["observed"]["records"]
        self.assertNotEqual(records[0]["obj"]["id"], records[1]["obj"]["id"])
        self.assertEqual(before, {f.id: f.row_sha256() for f in self.source.all()})

    def test_reversed_order_is_a_conflict_not_a_precision_request(self):
        result = self.check({"before": [4600, 4512]})
        gap = result["proof_gap"]["requirements"][0]
        self.assertEqual(gap["category"], "uncertain_or_wrong_time_order")
        self.assertEqual(gap["observed"]["order_status"], "reverse_order_conflict")
        self.assertIn("reverse", gap["reason"])
        self.assertIn("precision alone cannot reverse", gap["action"])

    def test_overlapping_times_require_independent_precision_without_rewriting_uncertainty(self):
        result = self.check({"copiedHere": [4703, 4702]})
        gap = result["proof_gap"]["requirements"][0]
        self.assertEqual(gap["category"], "uncertain_or_wrong_time_order")
        self.assertEqual(gap["observed"]["order_status"], "overlapping_or_insufficiently_separated")
        self.assertIn("more precise timestamp", gap["action"])
        self.assertIn("do not narrow it", gap["action"])
        self.assertGreaterEqual(gap["observed"]["combined_uncertainty_us"], gap["observed"]["gap_us"])

    def test_same_record_cannot_be_repaired_by_more_precision(self):
        result = self.check({"before": [4512, 4512]})
        gap = result["proof_gap"]["requirements"][0]
        self.assertEqual(gap["observed"]["order_status"], "same_record")
        self.assertIn("More precision cannot", gap["action"])

    def test_wrong_type_names_required_and_actual_kinds(self):
        result = self.check({"usbConnected": [4600]})
        gap = result["proof_gap"]["requirements"][0]
        self.assertEqual(gap["category"], "wrong_record_type")
        self.assertEqual(gap["required"]["kind"], "usbInsert")
        self.assertEqual(gap["observed"]["kind"], "lnkTarget")
        self.assertIn("Do not relabel", gap["action"])

    def test_wrong_constant_is_a_value_conflict(self):
        result = self.check({"tagged": [4512, "obj", 9002, 50]})
        gaps = result["proof_gap"]["requirements"]
        gap = next(g for g in gaps if g.get("required", {}).get("relation") == "encoded value equality")
        self.assertEqual(gap["category"], "contradictory_identity_or_value")
        self.assertEqual(gap["required"]["value_id"], 50)
        self.assertNotEqual(gap["observed"]["aux"]["id"], 50)

    def test_unsupported_form_and_malformed_claim_are_distinct_and_do_not_run_lean(self):
        for raw, category in (({"securelyWiped": [4512]}, "unsupported_rule_or_form"),
                              ({"before": [4512]}, "malformed_claim"),
                              ("not a claim object", "malformed_claim")):
            with self.subTest(raw=raw), patch.object(checker, "run_kernel") as kernel:
                gap = self.check(raw)["proof_gap"]
                self.assertEqual(gap["requirements"][0]["category"], category)
                kernel.assert_not_called()
        self.assertEqual(needs.malformed("invalid JSON")["requirements"][0]["category"], "malformed_claim")
        with patch.object(checker, "run_kernel") as kernel:
            bad_id = self.check({"usbConnected": [4512]}, name="bad id")
        kernel.assert_not_called()
        self.assertEqual(bad_id["proof_gap"]["requirements"][0]["category"], "malformed_claim")

    def test_composite_preserves_whole_refusal_and_only_failed_part_requirements(self):
        result = self.check({"both": [{"usbConnected": [4512]}, {"usbConnected": [4600]},
                                      {"before": [4600, 4512]}]})
        self.assertEqual(result["status"], "rejected")
        self.assertEqual([part["ok"] for part in result["parts"]], [True, False, False])
        gap = result["proof_gap"]
        self.assertIn("whole claim", gap["summary"])
        self.assertEqual([g["required"]["claim_part"] for g in gap["requirements"]],
                         [{"usbConnected": [4600]}, {"before": [4600, 4512]}])

    def test_census_mismatch_is_about_extracted_records_not_reality(self):
        result = self.check({"exactly": ["usbInsert", 999]})
        gap = result["proof_gap"]["requirements"][0]
        actual = len([f for f in self.source.all() if f.kind == "usbInsert"])
        self.assertEqual(gap["observed"]["count"], actual)
        self.assertEqual(gap["required"]["count"], 999)
        self.assertIn("not all real-world events", gap["action"])

    def test_unclassified_diagnostic_does_not_infer_evidence_or_invoke_kernel(self):
        part = claims.parse({"usbConnected": [4512]})
        with patch.object(checker, "run_kernel") as kernel:
            gap = needs.diagnose({"usbConnected": [4512]}, self.source, parsed=part,
                facts=self.source.get([4512]), parts=[{"part": {"usbConnected": [4512]},
                                                     "ok": False, "bricks": ["FAIL future-obligation"]}])
        kernel.assert_not_called()
        self.assertEqual(gap["requirements"][0]["category"], "execution_or_unclassified")

    def test_capacity_limit_is_not_missing_evidence_or_permission_to_drop_records(self):
        with patch.object(claims, "MAX_CENSUS", 0), patch.object(checker, "run_kernel") as kernel:
            result = self.check({"exactly": ["usbInsert", 0]})
        kernel.assert_not_called()
        gap = result["proof_gap"]["requirements"][0]
        self.assertEqual(gap["category"], "execution_or_unclassified")
        self.assertIn("capacity limit", gap["reason"])
        self.assertIn("Do not present a partial table", gap["action"])

    def test_diagnostic_failure_preserves_original_refusal_without_exposing_exception_details(self):
        with patch.object(needs, "diagnose", side_effect=RuntimeError("private exception detail")):
            result = self.check({"before": [4512, 999999]})
        self.assertEqual(result["status"], "rejected")
        self.assertIn("not in the evidence DB", result["reason"])
        self.assertEqual(result["proof_gap"]["requirements"][0]["category"], "execution_or_unclassified")
        self.assertNotIn("private exception detail", json.dumps(result["proof_gap"]))

    def test_valid_certificate_remains_unchanged_and_reverifies(self):
        result = self.check({"usbMountedAs": [4512, 4513]}, name="Valid")
        self.assertEqual(result["status"], "verified")
        self.assertNotIn("proof_gap", result)
        self.assertEqual(result["axioms"], [])
        self.assertEqual(verify(result, self.source), [])


if __name__ == "__main__":
    unittest.main()
