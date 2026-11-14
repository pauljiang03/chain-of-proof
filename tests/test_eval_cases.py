"""Case-independent answer evaluation, timezone isolation, and honest denominators."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from eval import memory_baseline, report_coverage, score


def reference(items, **metadata):
    return {"source": "Independent case", "tolerance_s": 2,
            "items": [{"id": name, "question": question, "expect": expect}
                      for name, question, expect in items], **metadata}


def record(obj="new clue", utc="2031-08-12T06:00:00Z", number=1):
    return {"id": number, "kind": "webSearch", "obj_text": obj, "aux_text": "",
            "t": score._us(utc), "res": 1, "prov": {"exhibit": "Laptop Z"}}


def run_for(rows):
    return {"findings": [{"finding_id": f"finding-{r['id']}", "strength": "strong",
                          "parts": [{"part": {"searched": [r["id"]]}}], "cited_facts": [r]}
                         for r in rows],
            "stats": {"proposals": len(rows), "verified": len(rows), "rejected": 0,
                      "by_strength": {"strong": len(rows)}}}


class CaseMatching(unittest.TestCase):
    def test_timezone_is_shared_by_extraction_run_answers_and_gate_selectors(self):
        expect = {"kind": "webSearch", "obj": "new clue", "local_day": "2031-08-11"}
        ref = reference([("row-alpha", "investigation-A", expect)], time_zone="America/Los_Angeles")
        rows = [record()]
        answers = [{"kind": "webSearch", "obj": "new clue", "utc": "2031-08-12T06:00:00Z"}]
        labeled = {"facts": {"clue": expect}}
        self.assertEqual(score.score_extraction(ref, rows)[0]["status"], "match")
        self.assertTrue(score.score_run(ref, run_for(rows))["items"][0]["certified"])
        self.assertEqual(score.score_answers(ref, answers)["matched"], 1)
        self.assertIsNotNone(score.resolve(labeled, rows, 2, score.reference_zone(ref))["clue"])
        self.assertEqual(score.score_extraction(ref, rows, "America/New_York")[0]["status"], "time_differs")
        self.assertFalse(score.score_run(ref, run_for(rows), "America/New_York")["items"][0]["certified"])
        self.assertEqual(score.score_answers(ref, answers, "America/New_York")["matched"], 0)
        self.assertIsNone(score.resolve(labeled, rows, 2, "America/New_York")["clue"])

    def test_unfamiliar_case_must_declare_local_timezone(self):
        ref = reference([("one", "arbitrary label", {"kind": "webSearch", "local_day": "2031-08-11"})])
        with self.assertRaisesRegex(ValueError, "no time_zone"):
            score.score_extraction(ref, [record()])
        with self.assertRaisesRegex(ValueError, "explicit time_zone"):
            score.time_match(ref["items"][0]["expect"], record(), 2)
        with self.assertRaisesRegex(ValueError, "IANA"):
            score.reference_zone(ref, "some case's local time")
        ref.update(source="NIST CFReDS Data Leakage Case, legacy", time_zone="legacy prose about EDT")
        self.assertEqual(score.reference_zone(ref), "America/New_York")

    def test_every_item_required_for_a_fully_answered_question(self):
        one = {"kind": "webSearch", "obj": "first"}
        two = {"kind": "webSearch", "obj": "second"}
        ref = reference([("a", "complete", one), ("b", "complete", two),
                         ("c", "partial", one), ("d", "partial", None),
                         ("e", "unanswered", {"kind": "webSearch", "obj": "missing"})])
        answers = [{"kind": "webSearch", "obj": "first"}, {"kind": "webSearch", "obj": "second"}]
        external = score.score_answers(ref, answers)
        internal = score.score_run(ref, run_for([record("first"), record("second", number=2)]))
        for result in (external, internal):
            q = result["question_summary"]
            self.assertEqual({k: q[k] for k in ("total", "complete", "partial", "unanswered")},
                             {"total": 3, "complete": 1, "partial": 1, "unanswered": 1})
            self.assertEqual(q["accuracy"], 1 / 3)
        self.assertEqual((external["matched"], external["reference_rows"]), (3, 5))

    def test_negative_and_unsupported_answers_never_receive_automatic_credit(self):
        expect = {"kind": "webSearch", "obj": "new clue"}
        ref = reference([("a", "absence", {**expect, "absent": True}),
                         ("b", "positive", expect), ("c", "unsupported", None)])
        result = score.score_answers(ref, [{**expect, "negated": True},
                                          {**expect, "status": "unsupported"}])
        self.assertEqual(result["matched"], 0)
        self.assertEqual(result["reference_rows"], 3)
        self.assertEqual(len(result["incompatible_answers"]), 2)
        self.assertEqual([i["status"] for i in result["items"]],
                         ["not_expressible", "missing", "not_expressible"])
        self.assertFalse(score.matches({**expect, "absent": True}, record(), 2))

    def test_untimed_wrong_time_wrong_exhibit_and_extra_answers_remain_distinct(self):
        timed = {"kind": "webSearch", "utc": "2031-08-12T06:00:00Z"}
        ref = reference([("a", "A", {**timed, "obj": "untimed"}),
                         ("b", "B", {**timed, "obj": "wrong time"}),
                         ("c", "C", {**timed, "obj": "wrong exhibit", "exhibit": "Laptop Z"}),
                         ("d", "D", {**timed, "obj": "correct", "exhibit": "Laptop Z"})])
        result = score.score_answers(ref, [
            {"kind": "webSearch", "obj": "untimed"},
            {"kind": "webSearch", "obj": "wrong time", "utc": "2031-08-12T07:00:00Z", "res": 10**15},
            {**timed, "obj": "wrong exhibit", "exhibit": "Different laptop"},
            {**timed, "obj": "correct", "utc": "2031-08-11T23:00:00.000001-07:00", "exhibit": "Laptop Z"},
            {**timed, "obj": "additional assertion"},
            {**timed, "obj": "broken", "utc": "yesterday"}])
        self.assertEqual([i["status"] for i in result["items"]],
                         ["untimed", "time_differs", "missing", "match"])
        self.assertEqual(result["unassessed_answer_indices"], [1, 2, 3, 5])
        self.assertEqual(len(result["incompatible_answers"]), 1)
        self.assertNotIn("false_positives", result)

    def test_prose_and_memory_diagnostics_use_declared_zone_without_ny_fallback(self):
        ref = reference([("x", "label-x", {"kind": "webSearch", "obj": "new clue",
                                             "utc": "2031-08-12T06:00:00Z"})],
                        time_zone="America/Los_Angeles")
        self.assertTrue(report_coverage.score(ref, "new clue at 23:00:00")["items"][0]["with_time"])
        self.assertFalse(report_coverage.score(ref, "new clue at 02:00:00")["items"][0]["with_time"])
        ref["items"][0]["expect"].pop("utc")
        ref["items"][0]["expect"]["local_day"] = "2031-08-11"
        result = memory_baseline.score(ref, [record()])
        self.assertTrue(result["items"][0]["full"])
        self.assertIn("Qlabel-x", memory_baseline.report(result))


class CaseFiles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir="/private/tmp")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ref = self.write("reference.json", reference([
            ("r", "custom question", {"kind": "webSearch", "obj": "new clue"})],
            question_names={"custom question": "Case-specific title"}))
        self.facts = self.write("facts.json", {"strings": {"0": "", "1": "new clue"},
            "facts": [{"id": 1, "kind": "webSearch", "t": score._us("2031-08-12T06:00:00Z"),
                       "res": 1, "obj": 1, "aux": 0}]})

    def write(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value))
        return path

    def test_arbitrary_reference_never_inherits_nist_gate_or_question_names(self):
        with patch.object(score, "score_gate") as gate:
            result = score.score(self.facts, reference_path=self.ref)
        gate.assert_not_called()
        self.assertFalse(result["gate_status"]["measured"])
        rendered = score.report(result)
        self.assertIn("not measured", rendered)
        self.assertIn("Case-specific title", rendered)
        self.assertFalse(result["headline"]["measured"])

    def test_nondefault_facts_and_external_answers_require_explicit_reference(self):
        with self.assertRaisesRegex(ValueError, "nondefault facts.*explicit --reference"):
            score.score(self.facts)
        answers = self.write("answers.json", [{"kind": "webSearch", "obj": "new clue"}])
        with self.assertRaisesRegex(ValueError, "answers require.*explicit --reference"):
            score.score(answers_path=answers)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            score.main(["--answers", str(answers), "--out", str(self.root / "not-written.json")])
        self.assertEqual(error.exception.code, 2)
        self.assertFalse((self.root / "not-written.json").exists())

    def test_explicit_probes_use_case_timezone_and_no_nist_known_miss_exemptions(self):
        ref = json.loads(self.ref.read_text())
        ref["time_zone"] = "America/Los_Angeles"
        self.ref.write_text(json.dumps(ref))
        gate_path = self.write("probes.json", {"facts": {
            "event": {"kind": "webSearch", "obj": "new clue", "local_day": "2031-08-11"}},
            "claims": [{"id": "T15", "label": True, "ask": "Case claim", "basis": "Fixture",
                        "claim": {"searched": ["event"]}}]})
        with patch.object(score.checker, "check", return_value={"status": "rejected", "claim": {}}) as checker:
            result = score.score(self.facts, reference_path=self.ref, labeled_claims_path=gate_path)
        checker.assert_called_once()
        self.assertTrue(result["gate_status"]["measured"])
        self.assertEqual(result["gate_status"]["known_misses"], [])
        self.assertEqual(result["gate"][0]["verdict"], "rejected")

    def test_external_cli_scores_custom_questions_without_loading_legacy_facts(self):
        answers = self.write("answers.json", [{"kind": "webSearch", "obj": "new clue"}])
        output = self.root / "result.json"
        with patch.object(score, "open_source") as source, contextlib.redirect_stdout(io.StringIO()) as out:
            rc = score.main(["--reference", str(self.ref), "--answers", str(answers), "--out", str(output)])
        source.assert_not_called()
        self.assertEqual(rc, 0)
        result = json.loads(output.read_text())
        self.assertEqual(result["headline"]["match_rate"], 1)
        self.assertEqual(result["headline"]["question_summary"]["complete"], 1)
        self.assertIn("Structured answer-item match rate: 1 / 1", out.getvalue())
        self.assertIn("Questions with every reference item matched", out.getvalue())
        self.assertFalse(result["gate_status"]["measured"])


if __name__ == "__main__":
    unittest.main()
