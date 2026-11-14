"""Conclusions are accepted only on top of certified findings, with no new details."""
import json
import tempfile
import unittest
from pathlib import Path

from agent.conclusions import Conclusions, details, ungrounded
from checker import export, report

SENTENCE = ("USB device 4C530012550531106501 was connected to the PC (2015-03-24 13:58:33 UTC). "
            "The file \\Secret Project Data\\design\\winter_storm.amr was created on it.")
LOG = [{"finding_id": "A001", "status": "verified", "english": SENTENCE, "strength": "strong"},
       {"finding_id": "A002", "status": "rejected", "reason": "no"}]


class Details(unittest.TestCase):
    def test_dates_times_serials_names_and_quotes_are_details_small_counts_are_not(self):
        got = details('On March 24, 2015 at 13:58 the stick 4C530012550531106501 held '
                      'winter_storm.amr and "Secret Project Data"; 3 files, on RM#2.')
        self.assertEqual(set(got), {"2015-03-24", "13:58", "4C530012550531106501",
                                    "winter_storm.amr", "Secret Project Data"})

    def test_a_detail_missing_from_the_cited_sentences_is_reported(self):
        self.assertEqual(ungrounded("It was connected at 13:58 on 24 March.", [SENTENCE]), [])
        self.assertEqual(ungrounded("It was connected at 09:58 on 25 March.", [SENTENCE]),
                         ["-03-25", "09:58"])


class Recording(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.c = Conclusions(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_conclusion_must_cite_certified_findings_of_this_run(self):
        self.assertEqual(self.c.add("He meant to take it.", [], LOG, "t")["status"], "rejected")
        self.assertEqual(self.c.add("He meant to take it.", ["A002"], LOG, "t")["status"], "rejected")
        self.assertEqual(self.c.add("He meant to take it.", ["A999"], LOG, "t")["status"], "rejected")

    def test_a_conclusion_cannot_carry_a_detail_no_cited_finding_has(self):
        r = self.c.add("The stick was used to copy budget.xlsx at 13:58.", ["A001"], LOG, "t")
        self.assertEqual(r["status"], "rejected")
        self.assertEqual(r["not_in_cited_findings"], ["budget.xlsx"])
        self.assertEqual(self.c.all(), [])

    def test_an_accepted_conclusion_is_stored_as_judgment_and_exported_apart_from_findings(self):
        r = self.c.add("The personal stick was connected to take winter_storm.amr out.",
                       ["A001"], LOG, "t")
        self.assertEqual((r["status"], r["conclusion_id"], r["strength"]), ("accepted", "C001", "judgment"))
        (Path(self.tmp.name) / "proposals.jsonl").write_text("\n".join(json.dumps(p) for p in LOG))
        run = export.bundle(Path(self.tmp.name), "case")
        self.assertEqual([c["conclusion_id"] for c in run["conclusions"]], ["C001"])
        self.assertEqual(run["findings"], [])              # a conclusion is never a finding
        text = report.render(run)
        self.assertNotIn("He meant", text)
        self.assertNotIn("(inference, unverified)", text)
        self.assertNotIn("The personal stick", text)
        text = report.render(run, include_judgments=True)
        self.assertIn("(inference, unverified) The personal stick", text)
        self.assertLess(text.index("## Certified findings"), text.index("## Appendix: unverified"))


if __name__ == "__main__":
    unittest.main()
