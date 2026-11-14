"""Statements about all the records of one kind: counted by the kernel, completeness by
the verifier."""
import json
import tempfile
import unittest
from pathlib import Path

from checker import check as checker
from checker import claims
from checker.facts import open_source
from verifier.verify import verify

ROOT = Path(__file__).resolve().parent.parent
FACTS = ROOT / "evidence" / "case_facts.json"


class Census(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = open_source(FACTS)
        cls.usb = [f for f in cls.source.all() if f.kind == "usbInsert"]
        cls.serials = {f.obj for f in cls.usb}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def check(self, claim, fid="X1"):
        return checker.check(claim, fid, self.source, "q", self.tmp.name)

    def test_the_true_count_is_certified_without_axioms(self):
        r = self.check({"exactlyDistinct": ["usbInsert", "obj", len(self.serials)]})
        self.assertEqual(r["status"], "verified")
        self.assertEqual(r["axioms"], [])
        self.assertEqual({c["id"] for c in r["cited_facts"]}, {f.id for f in self.usb})
        self.assertIn("is not counted", r["english"])          # the limit is always stated

    def test_a_wrong_count_is_refused_and_says_the_real_one(self):
        r = self.check({"exactly": ["usbInsert", len(self.usb) + 1]})
        self.assertEqual(r["status"], "rejected")
        self.assertIn(f"holds {len(self.usb)}, not {len(self.usb) + 1}", r["parts"][0]["bricks"][0])
        r = self.check({"exactlyWith": ["usbInsert", "obj", self.usb[0].obj, 0]}, "X2")
        self.assertEqual(r["status"], "rejected")                # "never connected" is false

    def test_no_record_of_a_kind_can_be_stated(self):
        r = self.check({"exactly": ["volumeMount", 0]})
        self.assertEqual(r["status"], "verified")
        self.assertIn("no volume mount record", r["english"])

    def test_a_census_stands_alone(self):
        with self.assertRaises(claims.ClaimError):
            claims.parse({"both": [{"exactly": ["usbInsert", 4]}, {"usbConnected": [self.usb[0].id]}]})
        with self.assertRaises(claims.ClaimError):
            claims.parse({"exactly": ["notAKind", 1]})

    def test_the_verifier_rejects_a_census_once_the_evidence_has_another_record(self):
        cert = self.check({"exactly": ["usbInsert", len(self.usb)]})
        self.assertEqual(verify(cert, self.source), [])
        data = json.loads(FACTS.read_text())
        extra = dict(next(f for f in data["facts"] if f["kind"] == "usbInsert"))
        extra["id"] = max(f["id"] for f in data["facts"]) + 1
        data["facts"].append(extra)
        grown = Path(self.tmp.name) / "grown.json"
        grown.write_text(json.dumps(data))
        problems = verify(cert, open_source(grown))
        self.assertTrue(problems and "differ" in problems[0], problems)


if __name__ == "__main__":
    unittest.main()
