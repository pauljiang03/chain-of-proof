"""End-to-end tests of the checker and verifier on the sample fixture.

    python3 -m unittest discover -s tests -t .

Needs the Lean toolchain (elan). Each test runs the real kernel.
"""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from checker import claims
from checker.check import check
from checker.facts import JsonFacts, open_source
from verifier.verify import verify

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "fixtures" / "sample_facts.json"
GOLDEN = {"both": [{"usbMountedAs": [4512, 4513]}, {"openedFromMount": [4600, 4513]},
                   {"before": [4512, 4600]}]}
NARRATIVE = {"both": [GOLDEN, {"tagged": [4600, "obj", 9001, 50]},
                      {"tagged": [4512, "obj", 9002, 51]}, {"before": [3100, 4512]}]}


class CheckerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = JsonFacts(FIXTURE)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_check(self, claim, fid="T1"):
        return check(claim, fid, self.src, out_dir=self.out)

    def test_golden_certificate_is_kernel_checked_with_no_axioms(self):
        r = self.run_check(GOLDEN, "F7")
        self.assertEqual(r["status"], "verified", r)
        self.assertEqual(r["trust_tier"], "kernel")
        self.assertEqual(r["axioms"], [])
        self.assertEqual(r["rules"], ["R1", "R2", "R3"])
        self.assertEqual(r["strength"], "strong")
        self.assertIn("SAMPLE-SERIAL-RM2", r["english"])
        self.assertTrue((self.out / "F7.lean").exists())
        self.assertEqual(verify(json.loads((self.out / "F7.json").read_text()), self.src), [])

    def test_narrative_with_tags_and_strength_labels(self):
        r = self.run_check(NARRATIVE, "N1")
        self.assertEqual(r["status"], "verified", r)
        self.assertEqual((r["strength"], r["axioms"]), ("strong", []))
        self.assertIn('is tagged "unauthorized-device" (rule: device serial is not on', r["english"])
        # one heuristic set, or one LLM-labeled tag, lowers the whole finding
        self.assertEqual(self.run_check({"copiedHere": [4701, 4700]}, "H1")["strength"], "heuristic")
        judged = self.run_check({"both": [NARRATIVE, {"tagged": [3100, "obj", 9003, 52]}]}, "J1")
        self.assertEqual((judged["status"], judged["strength"]), ("verified", "judgment"))
        self.assertIn("an LLM judgment", judged["english"])

    def test_wrong_order_is_rejected_and_names_the_failing_brick(self):
        r = self.run_check({"both": [{"usbMountedAs": [4512, 4513]}, {"before": [4600, 4512]}]},
                           "Rejected1")
        self.assertEqual(r["status"], "rejected")
        self.assertEqual([p["ok"] for p in r["parts"]], [True, False])
        self.assertEqual(r["parts"][1]["bricks"], ["FAIL before 4600 4512"])
        self.assertFalse((self.out / "Rejected1.json").exists())
        self.assertFalse((self.out / "Rejected1.lean").exists())

    def test_lnk_cannot_be_tied_to_another_devices_volume(self):
        # 4600 was opened from RM2's volume; 4511 is RM1's mount.
        r = self.run_check({"both": [{"usbMountedAs": [4510, 4511]},
                                     {"openedFromMount": [4600, 4511]}]})
        self.assertEqual(r["status"], "rejected")
        self.assertEqual(r["parts"][1]["bricks"][-1], "FAIL link 4600 (aux) 4511 (aux)")

    def test_order_within_timestamp_uncertainty_is_not_certified(self):
        # modified 1 s before created, but FAT mtime is only good to 2 s
        self.assertEqual(self.run_check({"copiedHere": [4703, 4702]})["status"], "rejected")
        self.assertEqual(self.run_check({"copiedHere": [4701, 4700]}, "C1")["status"], "verified")

    def test_same_path_on_another_volume_is_not_a_copy_here(self):
        # 4704 is the same path last modified on RM1's volume, 4701 its creation on RM2's
        self.assertEqual(self.run_check({"copiedHere": [4701, 4704]})["status"], "rejected")

    def test_a_tag_cannot_be_placed_before_a_real_event(self):
        self.assertEqual(self.run_check({"before": [9001, 4512]})["status"], "rejected")
        # and a tag about one entity does not attach to another
        self.assertEqual(self.run_check({"tagged": [4510, "obj", 9002, 51]})["status"], "rejected")

    def test_unknown_fact_and_malformed_claims_never_reach_lean(self):
        self.assertIn("not in the evidence DB", self.run_check({"before": [4512, 999]})["reason"])
        for bad in [{"before": [1]}, {"before": ["4512", 4600]}, {"nope": [1, 2]},
                    {"before": [4512, 4600], "x": 1}, "before", {"both": [{"before": [1, 2]}]},
                    {"before": [True, 2]}, {"before": [-1, 2]},
                    {"tagged": [1, "obj) (.before 1 2", 3, 4]}, {"tagged": [1, "kind", 3, 4]}]:
            with self.assertRaises(claims.ClaimError, msg=repr(bad)):
                claims.parse(bad)
        self.assertEqual(self.run_check(GOLDEN, "F7; import Evil")["status"], "rejected")

    def test_verifier_catches_tampering(self):
        self.run_check(GOLDEN, "F9")
        cert = json.loads((self.out / "F9.json").read_text())
        english = copy.deepcopy(cert)
        english["english"] = english["english"].replace("RM2", "RM1")
        self.assertTrue(verify(english, self.src))
        fact = copy.deepcopy(cert)
        fact["cited_facts"][0]["row_sha256"] = "0" * 64
        self.assertTrue(verify(fact, self.src))
        claim = copy.deepcopy(cert)
        claim["claim"] = {"before": [4600, 4512]}
        self.assertTrue(verify(claim, self.src))

    def test_verifier_refuses_untrusted_identifiers_before_lean_generation(self):
        cert = self.run_check(GOLDEN, "SafeID")
        for invalid in (None, 1, "", "F7\nend Cert.F7", "F7; import Evil", "x" * 33):
            altered = dict(cert, finding_id=invalid)
            with self.subTest(finding_id=invalid), patch("verifier.verify.run_kernel") as kernel:
                self.assertTrue(verify(altered, self.src))
                kernel.assert_not_called()

    def test_verifier_rejects_changed_copies_even_with_original_hash_and_english(self):
        self.run_check(GOLDEN, "F10")
        cert = json.loads((self.out / "F10.json").read_text())
        for field, value in (("t", 123), ("obj_text", "fabricated entity"),
                             ("prov", {"artifact": "invented"}), ("res", True)):
            altered = copy.deepcopy(cert)
            altered["cited_facts"][0][field] = value
            self.assertTrue(verify(altered, self.src), field)
        for field, value in (("rules", []), ("status", "rejected")):
            altered = copy.deepcopy(cert)
            altered[field] = value
            self.assertTrue(verify(altered, self.src), field)
        altered = copy.deepcopy(cert)
        altered["parts"][0]["english"] = "Invented finding in the certificate viewer"
        self.assertTrue(verify(altered, self.src))
        altered = copy.deepcopy(cert)
        altered["cited_facts"].append(altered["cited_facts"][0])
        self.assertTrue(verify(altered, self.src))

    def test_duckdb_source_matches_fixture(self):
        try:
            import duckdb
        except ImportError:
            self.skipTest("duckdb not installed")
        data = json.loads(FIXTURE.read_text())
        path = self.out / "evidence.duckdb"
        db = duckdb.connect(str(path))
        db.execute((ROOT / "extractor" / "schema.sql").read_text())
        db.executemany("INSERT INTO strings VALUES (?, ?)",
                       [(int(k), v) for k, v in data["strings"].items()])
        db.executemany("INSERT INTO facts VALUES (?, ?, ?, ?, ?, ?, ?)",
                       [(f["id"], f["kind"], f["t"], f["res"], f["obj"], f["aux"],
                         json.dumps(f["prov"])) for f in data["facts"]])
        db.close()
        r = check(GOLDEN, "F7", open_source(path), out_dir=self.out / "duck")
        self.assertEqual(r["status"], "verified", r)
        self.assertEqual(r["cited_facts"][0]["row_sha256"],
                         self.src.get([4512])[4512].row_sha256())


if __name__ == "__main__":
    unittest.main()
