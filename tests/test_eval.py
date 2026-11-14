"""The scorer and the miner, on the committed evidence file from the real images."""
import json
import unittest
from pathlib import Path

from checker.facts import open_source
from eval import score
from miner import mine

ROOT = Path(__file__).resolve().parent.parent
FACTS = ROOT / "evidence" / "case_facts.json"


class RealEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = open_source(FACTS)
        cls.rows = score.rows_of(cls.source)
        cls.reference = json.loads(score.REFERENCE.read_text())

    def test_extraction_matches_the_answer_key(self):
        result = score.score_extraction(self.reference, self.rows)
        status = [r["status"] for r in result]
        # a drop here means the extractor lost rows the answer key confirms
        self.assertGreaterEqual(status.count("match"), 95)
        self.assertEqual(status.count("time_differs"), 0)

    def test_gate_refuses_every_false_claim_and_certifies_the_true_ones(self):
        labeled = json.loads(score.LABELED.read_text())
        result = score.score_gate(labeled, self.source, self.rows, self.reference["tolerance_s"])
        for r in result:
            if not r["label"]:
                self.assertEqual(r["verdict"], "rejected", r["id"])
            elif r["id"] not in score.KNOWN_MISSES:
                self.assertEqual(r["verdict"], "verified", r["id"])
        # the documented miss: true per NIST, not provable by strong rules after the format
        self.assertEqual(next(r for r in result if r["id"] == "T15")["verdict"], "rejected")

    def test_miner_is_deterministic(self):
        first = mine.candidates(self.source)
        self.assertEqual(first, mine.candidates(open_source(FACTS)))
        self.assertGreater(len(first), 50)

    def test_a_row_counts_only_if_a_sentence_states_it(self):
        finding = {"finding_id": "X", "strength": "strong",
                   "parts": [{"part": {"tagged": [7, "obj", 9, 3]}}],
                   "cited_facts": [{"id": 7, "kind": "webSearch", "t": 0, "obj_text": "x", "aux_text": ""}]}
        self.assertEqual(score.stated_rows(finding), [])
        finding["parts"] = [{"part": {"searched": [7]}}]
        self.assertEqual([r["id"] for r in score.stated_rows(finding)], [7])


if __name__ == "__main__":
    unittest.main()
