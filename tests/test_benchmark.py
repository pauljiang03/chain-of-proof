"""Neutral typed-answer scoring, including deliberately adversarial submissions."""
import contextlib
import io
import itertools
import json
import tempfile
import unittest
from pathlib import Path

from eval import benchmark as b


def reference(*expected, **metadata):
    return {"schema_version": 2, "case_id": "independent-fixture",
            "questions": [{"id": str(i), "prompt": f"Question {i}", "expected": value}
                          for i, value in enumerate(expected, 1)], **metadata}


def answers(*values):
    return {"schema_version": 2, "case_id": "independent-fixture",
            "answers": [{"question_id": str(i), "status": "answered", "answer": value}
                        for i, value in enumerate(values, 1)]}


class TypedAnswers(unittest.TestCase):
    def test_false_null_zero_empty_and_unknown_are_distinct(self):
        expected = [False, None, 0, "", [], {}]
        perfect = b.score(reference(*expected), answers(*expected))
        self.assertEqual(perfect["question_counts"]["fully_correct"], 6)
        self.assertEqual(perfect["atomic"]["true_positive"], 6)
        wrong = b.score(reference(False, None, 0), answers(0, "null", False))
        self.assertEqual(wrong["question_counts"]["incorrect"], 3)
        self.assertEqual(wrong["atomic"]["wrong"], 3)
        unknown = answers(False)
        unknown["answers"][0]["status"] = "unknown"
        result = b.score(reference(False), unknown)
        self.assertEqual(result["question_counts"]["unanswered"], 1)
        self.assertEqual(result["atomic"]["true_positive"], 0)
        self.assertEqual(result["questions"][0]["response_status"], "unknown")

    def test_empty_input_never_reports_vacuous_perfection(self):
        empty = b.score(reference(), answers())
        self.assertIsNone(empty["fully_correct_question_rate"])
        self.assertIsNone(empty["atomic"]["match_rate"])
        self.assertFalse(empty["perfect_submission"])
        missing = b.score(reference([], {}, None), answers())
        self.assertEqual(missing["atomic"]["missing"], 3)
        self.assertEqual(missing["question_counts"]["unanswered"], 3)

    def test_required_objects_partial_answers_and_extra_fields(self):
        ref = reference({"os": "ExampleOS", "version": 2, "enabled": False})
        result = b.score(ref, answers({"os": "ExampleOS", "version": 9, "extra": "assertion"}))
        self.assertEqual(result["questions"][0]["atomic"], {"true_positive": 1, "missing": 2, "wrong": 2})
        self.assertEqual(result["questions"][0]["rubric_label"], "PARTIAL")
        correct_plus_extra = b.score(ref, answers({"os": "ExampleOS", "version": 2,
                                                  "enabled": False, "extra": "assertion"}))
        self.assertEqual(correct_plus_extra["question_counts"]["fully_correct"], 0)
        self.assertEqual(correct_plus_extra["atomic"]["wrong"], 1)

    def test_unordered_lists_keep_multiplicity_and_penalize_shotgun_answers(self):
        ref = reference(["a", "a", "b"])
        perfect = b.score(ref, answers(["b", "a", "a"]))
        self.assertTrue(perfect["perfect_submission"])
        missing = b.score(ref, answers(["a", "b"]))
        self.assertEqual(missing["atomic"]["true_positive"], 2)
        self.assertEqual(missing["atomic"]["missing"], 1)
        extra = b.score(reference([True]), answers([True, False]))
        self.assertEqual(extra["questions"][0]["status"], "partial")
        self.assertEqual(extra["atomic"]["wrong"], 1)
        self.assertEqual(extra["atomic"]["extra_or_unexpected_atoms"], 1)
        self.assertEqual(extra["atomic"]["mismatched_value_atoms"], 0)
        duplicated = b.score(reference(["one"]), answers(["one", "one"]))
        self.assertFalse(duplicated["perfect_submission"])
        self.assertEqual(duplicated["atomic"]["wrong"], 1)

    def test_unordered_objects_use_global_assignment_and_preserve_audit_paths(self):
        expected = [{"id": "same", "value": "x"}, {"id": "same", "value": "y"}]
        actual = [{"id": "same", "value": "y"}, {"id": "same", "value": "x"}]
        result = b.score(reference(expected), answers(actual))
        self.assertEqual(result["atomic"]["true_positive"], 4)
        event = next(e for e in result["questions"][0]["audit"] if e["expected_path"] == "/0/value")
        self.assertEqual(event["answer_path"], "/answers/0/answer/1/value")
        # A greedy row assignment gets 9; the global assignment gets 17.
        self.assertEqual(b._assignment([[9, 8], [9, 0]]), [(0, 1), (1, 0)])
        self.assertEqual(b._assignment([[9, 8, 0], [9, 0, 10]]), [(0, 0), (1, 2)])
        for weights in ([[1, 3, 1], [4, 2, 0], [3, 0, 5]], [[-4, -2], [-1, -3]]):
            got = sum(weights[i][j] for i, j in b._assignment(weights))
            wanted = max(sum(weights[i][j] for i, j in enumerate(p))
                         for p in itertools.permutations(range(len(weights))))
            self.assertEqual(got, wanted)

    def test_ordered_lists_require_declared_order(self):
        ref = reference(["a", "b"])
        ref["questions"][0]["match"] = {"list_order": "ordered"}
        result = b.score(ref, answers(["b", "a"]))
        self.assertEqual(result["atomic"]["true_positive"], 0)
        self.assertEqual(result["question_counts"]["incorrect"], 1)

    def test_string_changes_require_declared_normalization(self):
        ref = reference("Some Name")
        self.assertEqual(b.score(ref, answers("some name"))["question_counts"]["incorrect"], 1)
        ref["questions"][0]["match"] = {"strings": "casefold_whitespace"}
        self.assertTrue(b.score(ref, answers("  SOME   name\n"))["perfect_submission"])
        ref = reference({"visits": [{"url": "https://host/a"}, {"url": "https://host/truncated"}]})
        ref["questions"][0]["match"] = {"string_modes": {"/visits/1/url": "prefix"}}
        submission = answers({"visits": [{"url": "https://host/truncated/more"}, {"url": "https://host/a"}]})
        self.assertTrue(b.score(ref, submission)["perfect_submission"])
        ref["questions"][0]["match"] = {"unrecognized_setting": "ignored?"}
        with self.assertRaisesRegex(ValueError, "unknown matching"):
            b.score(ref, submission)

    def test_duplicate_question_responses_prevent_full_credit(self):
        submitted = answers(False)
        submitted["answers"].append({"question_id": "1", "status": "answered", "answer": True})
        result = b.score(reference(False), submitted)
        self.assertEqual(result["questions"][0]["status"], "partial")
        self.assertEqual(result["atomic"]["wrong"], 1)
        self.assertFalse(result["perfect_submission"])

    def test_unexpected_questions_are_audited_and_prevent_perfect_submission(self):
        result = b.score(reference("correct"), answers("correct", "invented"))
        self.assertEqual(result["question_counts"]["total"], 1)
        self.assertEqual(result["atomic"]["wrong"], 1)
        self.assertEqual(result["unexpected_questions"][0]["question_id"], "2")
        self.assertFalse(result["perfect_submission"])

    def test_unevaluable_questions_stay_in_denominator(self):
        ref = reference("answer")
        ref["questions"].extend([
            {"id": "2", "prompt": "Interpret a diagram", "evaluation": {
                "status": "unevaluable", "reason": "No deterministic diagram contract yet"}},
            {"id": "3", "prompt": "Ambiguous source", "expected": {"field": "uncertain"},
             "evaluation": {"status": "unevaluable", "reason": "Source needs review"}}])
        result = b.score(ref, answers("answer"))
        self.assertEqual(result["fully_correct_question_rate"], 1 / 3)
        self.assertEqual(result["scorable_question_rate"], 1)
        self.assertEqual(result["question_counts"]["unevaluable"], 2)
        self.assertEqual(result["atomic"]["unscored_expected_atoms"], 1)
        self.assertEqual(result["atomic"]["match_rate"], .5)
        self.assertEqual(result["atomic"]["scorable_match_rate"], 1)
        self.assertIsNone(result["questions"][1]["unscored_expected_atoms"])


class TemporalAnswers(unittest.TestCase):
    def test_timestamp_wildcards_preserve_literal_null_values(self):
        ref = reference({"events": [{"time": None}, {"time": "2031-08-12T06:00:00Z"}]})
        ref["questions"][0]["match"] = {"timestamps": {"/events/*/time": {}}}
        self.assertTrue(b.score(ref, answers({"events": [{"time": "2031-08-12T06:00:00Z"},
                                                         {"time": None}]}))["perfect_submission"])

    def test_same_explicit_tolerance_for_every_submission_and_wildcard_paths(self):
        ref = reference({"events": [{"name": "a", "time": "2031-08-12T06:00:00Z"},
                                    {"name": "b", "time": "2031-08-12T07:00:00Z"}]})
        ref["questions"][0]["match"] = {"timestamps": {"/events/*/time": {"tolerance_seconds": 2}}}
        submitted = answers({"events": [{"name": "b", "time": "2031-08-12T00:00:02-07:00"},
                                        {"name": "a", "time": "2031-08-12T06:00:00.000001Z"}]})
        self.assertTrue(b.score(ref, submitted)["perfect_submission"])
        submitted["answers"][0]["answer"]["events"][0]["time"] = "2031-08-12T07:00:02.000001Z"
        result = b.score(ref, submitted)
        self.assertEqual(result["atomic"]["true_positive"], 3)
        self.assertEqual(result["atomic"]["wrong"], 1)

    def test_local_day_uses_declared_case_zone(self):
        ref = reference("2031-08-11", time_zone="America/Los_Angeles")
        ref["questions"][0]["match"] = {"timestamps": {"": {"granularity": "local_day"}}}
        submitted = answers("2031-08-12T06:00:00Z")
        self.assertTrue(b.score(ref, submitted)["perfect_submission"])
        ref["time_zone"] = "America/New_York"
        self.assertEqual(b.score(ref, submitted)["question_counts"]["incorrect"], 1)

    def test_naive_instants_require_zone_and_dst_ambiguity_is_not_guessed(self):
        ref = reference("2031-08-12T06:00:00")
        ref["questions"][0]["match"] = {"timestamps": {"": {}}}
        with self.assertRaisesRegex(ValueError, "declared time_zone"):
            b.score(ref, answers("2031-08-12T06:00:00Z"))
        ref["time_zone"] = "UTC"
        self.assertTrue(b.score(ref, answers("2031-08-12T06:00:00Z"))["perfect_submission"])
        ref = reference("2025-11-02T01:30:00", time_zone="America/New_York")
        ref["questions"][0]["match"] = {"timestamps": {"": {}}}
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            b.score(ref, answers("2025-11-02T05:30:00Z"))

    def test_date_only_value_cannot_satisfy_an_instant(self):
        ref = reference("2031-08-12T00:00:00Z")
        ref["questions"][0]["match"] = {"timestamps": {"": {}}}
        self.assertEqual(b.score(ref, answers("2031-08-12"))["question_counts"]["incorrect"], 1)


class RepresentationContracts(unittest.TestCase):
    def test_declared_path_root_preserves_drive_and_share_identities(self):
        ref = reference({"path": r"\Users\Someone\Notes\note.snt"})
        ref["questions"][0]["match"] = {"paths": {"/path": {
            "style": "windows", "root": "C:", "case_sensitive": False, "scope": "PC system volume"}}}
        self.assertTrue(b.score(ref, answers({"path": r"c:\users\Someone\Notes\note.snt"}))["perfect_submission"])
        self.assertTrue(b.score(ref, answers({"path": "C:/Users/Someone/Notes/note.snt"}))["perfect_submission"])
        for wrong in (r"D:\Users\Someone\Notes\note.snt", r"\\remote\share\Users\Someone\Notes\note.snt",
                      r"C:Users\Someone\Notes\note.snt", r"C:\Users\Someone\Notes\*.snt"):
            self.assertEqual(b.score(ref, answers({"path": wrong}))["question_counts"]["incorrect"], 1)

    def test_no_implicit_drive_stripping_and_no_implicit_product_aliases(self):
        ref = reference({"path": r"\folder\file.db"})
        self.assertFalse(b.score(ref, answers({"path": r"C:\folder\file.db"}))["perfect_submission"])
        ref["questions"][0]["match"] = {"paths": {"/path": {"style": "windows"}}}
        self.assertFalse(b.score(ref, answers({"path": r"C:\folder\file.db"}))["perfect_submission"])
        ref = reference({"browsers": [{"name": "Google Chrome", "version": "9.8"}], "upgraded": True})
        self.assertEqual(b.score(ref, answers({"browsers": [{"name": "Chrome"}]}))["atomic"]["true_positive"], 0)
        ref["questions"][0]["match"] = {"string_aliases": {"/browsers/*/name": [["Google Chrome", "Chrome"]]}}
        result = b.score(ref, answers({"browsers": [{"name": "Chrome"}]}))
        self.assertEqual(result["atomic"]["true_positive"], 1)
        self.assertEqual(result["atomic"]["missing"], 2)
        self.assertEqual(result["questions"][0]["status"], "partial")
        self.assertFalse(b.score(ref, answers({"browsers": [{"name": "Chromium", "version": "9.8"}], "upgraded": True}))["perfect_submission"])


class BenchmarkInterface(unittest.TestCase):
    def test_case_identity_and_reference_errors_are_rejected(self):
        submitted = answers("yes")
        submitted["case_id"] = "other-case"
        with self.assertRaisesRegex(ValueError, "exact case_id"):
            b.score(reference("yes"), submitted)
        ref = reference("yes")
        ref["questions"].append(ref["questions"][0].copy())
        with self.assertRaisesRegex(ValueError, "unique"):
            b.score(ref, answers("yes"))

    def test_cli_emits_auditable_provenance_and_repeatable_output(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            root = Path(tmp)
            ref, submitted, out = root / "reference.json", root / "answers.json", root / "results.json"
            ref.write_text(json.dumps(reference(False)))
            submitted.write_text(json.dumps(answers(False)))
            args = ["--reference", str(ref), "--answers", str(submitted), "--out", str(out)]
            with contextlib.redirect_stdout(io.StringIO()) as printed:
                self.assertEqual(b.main(args), 0)
            first = out.read_text()
            result = json.loads(first)
            self.assertIn("FOUND 1", printed.getvalue())
            self.assertEqual(len(result["inputs"]["reference"]["sha256"]), 64)
            self.assertEqual(len(result["scorer_sha256"]), 64)
            with contextlib.redirect_stdout(io.StringIO()):
                b.main(args)
            self.assertEqual(out.read_text(), first)


if __name__ == "__main__":
    unittest.main()
