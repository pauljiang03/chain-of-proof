"""Literal A/C answer scoring stays separate from facts, proofs, and B retention."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from comparison.ablation import answers
from eval import benchmark, submission


ROOT = Path(__file__).resolve().parent.parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class AblationAnswers(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name).resolve()
        self.summary = self.directory / "summary.md"
        self.questions = self.directory / "questions.json"
        self.reference = self.directory / "reference.json"
        self.public = {"schema_version": 2, "case_id": "synthetic", "time_zone": "UTC",
                       "contract_revision": "frozen-1", "questions": [
                           {"id": f"Q{i}", "prompt": f"Public question {i}", "answer_schema": {}}
                           for i in range(1, 5)]}
        self.key = {"schema_version": 2, "case_id": "synthetic", "time_zone": "UTC",
                    "public_contract_revision": "frozen-1", "review_status": "draft_requires_independent_review",
                    "evaluation_use": "development_not_blind", "transcription": {"independent_review_completed": False},
                    "questions": [{"id": f"Q{i}", "prompt": f"Public question {i}", "expected": value,
                                   "evaluation": {"status": "scorable"}}
                                  for i, value in enumerate(("correct", False, None, "unreviewed"), 1)]}
        self.key["questions"][-1]["evaluation"] = {"status": "unevaluable", "reason": "Unresolved synthetic reference."}
        self.literal = {"schema_version": 2, "case_id": "synthetic", "answers": [
            {"question_id": "Q1", "status": "answered", "answer": "WRONG"},
            {"question_id": "Q2", "status": "answered", "answer": False},
            {"question_id": "Q3", "status": "answered", "answer": None},
            {"question_id": "Q4", "status": "unknown"}]}
        self.write_contract()
        self.set_answers(self.literal)

    def write_contract(self):
        self.questions.write_text(json.dumps(self.public), encoding="utf-8")
        self.reference.write_text(json.dumps(self.key), encoding="utf-8")

    def set_answers(self, literal):
        block = json.dumps(literal, indent=3, ensure_ascii=False) + "\n"
        self.summary.write_text("Actual final text; no offline repair.\n\n```json\n" + block + "```\n", encoding="utf-8")
        return block.encode()

    def hashes(self):
        return {name: sha(path.read_bytes()) for name, path in (
            ("summary", self.summary), ("questions", self.questions), ("reference", self.reference))}

    def evaluate(self, arm="A", output="evaluation", hashes=None):
        return answers.evaluate_trial(self.summary, self.questions, self.reference,
                                      self.directory / output, arm=arm,
                                      expected_hashes=self.hashes() if hashes is None else hashes)

    def test_wrong_values_false_and_null_remain_literal_and_unverified(self):
        original = {path: path.read_bytes() for path in (self.summary, self.questions, self.reference)}
        expected_block = self.set_answers(self.literal)
        with patch("eval.submission.extract", wraps=submission.extract) as extract:
            result = self.evaluate()
        extract.assert_called_once()
        self.assertTrue(result["evaluation"]["measured"])
        self.assertEqual(result["evaluation"]["answer_verification"], "unverified")
        self.assertEqual(result["evaluation"]["claim_value_entailment"], "not_established")
        self.assertEqual(result["score"], benchmark.score(self.key, self.literal))
        self.assertEqual(result["score"]["question_counts"]["incorrect"], 1)
        self.assertEqual(result["score"]["question_counts"]["fully_correct"], 2)
        output = self.directory / "evaluation"
        self.assertEqual((output / "answers.json").read_bytes(), expected_block)
        self.assertEqual((output / "submission-block.txt").read_bytes(), expected_block)
        self.assertEqual(json.loads((output / "answers.json").read_text()), self.literal)
        self.assertEqual((output / "summary.md").read_bytes(), original[self.summary])
        for path, raw in original.items():
            self.assertEqual(path.read_bytes(), raw)
        provenance = json.loads((output / "provenance.json").read_text())
        self.assertEqual(provenance["answers_sha256"], sha(expected_block))
        self.assertEqual(provenance["answer_verification"], "unverified")
        self.assertIsNone(provenance["adapter"])
        self.assertNotIn("submission_origin", json.loads((output / "answers.json").read_text()))

    def test_a_and_c_use_the_identical_unchanged_benchmark(self):
        with patch("eval.benchmark.score", wraps=benchmark.score) as score:
            a = self.evaluate("A", "a")
            c = self.evaluate("C", "c")
        self.assertEqual(score.call_count, 2)
        self.assertEqual(score.call_args_list[0], score.call_args_list[1])
        self.assertEqual(a["score"], c["score"])
        self.assertEqual(a["evaluation"], c["evaluation"])
        self.assertEqual((self.directory / "a/answers.json").read_bytes(),
                         (self.directory / "c/answers.json").read_bytes())
        self.assertEqual(c["evaluation"]["answer_verification"], "unverified")

    def test_b_question_accuracy_is_not_implemented_or_fabricated(self):
        with patch("eval.benchmark.score", side_effect=AssertionError("B cannot receive question scores")):
            with self.assertRaisesRegex(ValueError, "claim retention"):
                self.evaluate("B")
        self.assertFalse((self.directory / "evaluation").exists())

    def test_missing_empty_unfenced_or_multiple_blocks_are_unavailable(self):
        literal = json.dumps(self.literal)
        summaries = ("", "The model stopped without final answers.", literal,
                     "```json\n" + literal + "\n```\n```json\n" + literal + "\n```\n",
                     "```json\n{broken\n```\n```json\n" + literal + "\n```\n")
        for index, text in enumerate(summaries):
            with self.subTest(index=index):
                self.summary.write_text(text)
                with patch("eval.benchmark.score", side_effect=AssertionError("must not score missing answers")):
                    result = self.evaluate(output=str(index))
                self.assertFalse(result["evaluation"]["measured"])
                self.assertEqual(result["evaluation"]["status"], "unavailable")
                self.assertIsNone(result["score"])
                self.assertFalse((self.directory / str(index) / "answers.json").exists())
                self.assertEqual(result["reference_contract"]["total_questions"], 4)
                self.assertEqual(result["reference_contract"]["unresolved_ids"], ["Q4"])

    def test_malformed_nonfinite_duplicate_keys_and_wrong_schema_have_no_fallback(self):
        invalid_values = []
        for change in ({"schema_version": 1}, {"case_id": "another"}, {"answers": []}):
            invalid_values.append(json.dumps({**self.literal, **change}))
        invalid_values += ["{broken", "[]", '{"answers":[],"answers":[]}',
                           json.dumps(self.literal).replace('"WRONG"', "NaN"),
                           json.dumps(self.literal).replace('"WRONG"', "1e999")]
        for index, block in enumerate(invalid_values):
            with self.subTest(index=index):
                self.summary.write_text("```json\n" + block + "\n```\n")
                with patch("eval.benchmark.score", side_effect=AssertionError("invalid input must not be scored")):
                    result = self.evaluate(output=str(index))
                self.assertIsNone(result["score"])
                self.assertFalse(result["evaluation"]["measured"])
                self.assertEqual((self.directory / str(index) / "submission-block.txt").read_text(), block + "\n")
                self.assertFalse((self.directory / str(index) / "answers.json").exists())

    def test_wrong_answer_status_missing_question_and_duplicate_ids_are_unavailable(self):
        variants = []
        for edit in ("missing", "duplicate", "status", "answer"):
            literal = copy.deepcopy(self.literal)
            if edit == "missing":
                literal["answers"].pop()
            elif edit == "duplicate":
                literal["answers"].append(literal["answers"][0])
            elif edit == "status":
                literal["answers"][0]["status"] = "verified"
            else:
                del literal["answers"][0]["answer"]
            variants.append(literal)
        for index, literal in enumerate(variants):
            self.set_answers(literal)
            result = self.evaluate(output=str(index))
            self.assertIsNone(result["score"])
            self.assertFalse(result["evaluation"]["measured"])

    def test_explicit_unknown_answers_are_measured_without_repair(self):
        literal = copy.deepcopy(self.literal)
        literal["answers"][0] = {"question_id": "Q1", "status": "unknown"}
        self.set_answers(literal)
        result = self.evaluate()
        self.assertTrue(result["evaluation"]["measured"])
        self.assertEqual(result["score"]["question_counts"]["unanswered"], 1)
        self.assertEqual(json.loads((self.directory / "evaluation/answers.json").read_text()), literal)

    def test_unreadable_final_text_has_no_score_but_original_bytes_are_retained(self):
        self.summary.write_bytes(b"\xff\xfe\x00")
        result = self.evaluate()
        self.assertIsNone(result["score"])
        self.assertEqual((self.directory / "evaluation/summary.md").read_bytes(), b"\xff\xfe\x00")

    def test_hash_mismatch_and_incomplete_hash_contract_fail_before_scoring_or_output(self):
        for name in ("summary", "questions", "reference", "missing"):
            values = self.hashes()
            if name == "missing":
                del values["summary"]
            else:
                values[name] = "0" * 64
            with self.subTest(name=name), patch("eval.benchmark.score", side_effect=AssertionError("hash check first")):
                with self.assertRaises(ValueError):
                    self.evaluate(hashes=values)
            self.assertFalse((self.directory / "evaluation").exists())

    def test_public_private_contract_mismatch_is_rejected_before_scoring(self):
        original = copy.deepcopy(self.key)
        for change in ("case_id", "time_zone", "revision", "prompt", "match", "ids"):
            self.key = copy.deepcopy(original)
            if change == "case_id":
                self.key["case_id"] = "another"
            elif change == "time_zone":
                self.key["time_zone"] = "America/New_York"
            elif change == "revision":
                self.key["public_contract_revision"] = "changed"
            elif change == "prompt":
                self.key["questions"][0]["prompt"] += " changed"
            elif change == "match":
                self.key["questions"][0]["match"] = {"strings": "casefold"}
            else:
                self.key["questions"][0]["id"] = "NEW"
            self.write_contract()
            with self.subTest(change=change), patch("eval.benchmark.score", side_effect=AssertionError("contract check first")):
                with self.assertRaises(ValueError):
                    self.evaluate()
            self.assertFalse((self.directory / "evaluation").exists())

    def test_public_contract_cannot_contain_private_fields(self):
        self.public["questions"][0]["expected"] = "correct"
        self.write_contract()
        with self.assertRaisesRegex(ValueError, "private"):
            self.evaluate()
        self.assertFalse((self.directory / "evaluation").exists())

    def test_only_declared_summary_public_and_private_inputs_are_opened(self):
        with patch.object(answers, "_read", wraps=answers._read) as reads, \
                patch("eval.nist_answers.generate", side_effect=AssertionError("no adapter")), \
                patch("checker.facts.open_source", side_effect=AssertionError("no facts")):
            self.evaluate()
        self.assertEqual([call.args[0] for call in reads.call_args_list],
                         [self.summary, self.questions, self.reference])

    def test_output_is_exclusive_and_refuses_traversal_and_symlinks(self):
        self.evaluate()
        output = self.directory / "evaluation"
        original = {path.name: path.read_bytes() for path in output.iterdir()}
        with self.assertRaises(FileExistsError):
            self.evaluate()
        self.assertEqual({path.name: path.read_bytes() for path in output.iterdir()}, original)
        for relative in ("../escaped", "linked/escaped"):
            if relative.startswith("linked"):
                (self.directory / "linked").symlink_to(self.directory, target_is_directory=True)
            with self.subTest(relative=relative):
                with self.assertRaises(ValueError):
                    self.evaluate(output=relative)
        self.assertFalse((self.directory / "escaped").exists())
        source = self.directory / "summary-link.md"
        source.symlink_to(self.summary)
        with self.assertRaisesRegex(ValueError, "symlink"):
            answers.evaluate_trial(source, self.questions, self.reference, self.directory / "new",
                                   arm="A", expected_hashes=self.hashes())

    def test_nist_reference_keeps_all_sixty_with_forty_six_provisional_fourteen_unresolved(self):
        self.questions = ROOT / "eval/benchmark_nist_questions.json"
        self.reference = ROOT / "eval/benchmark_nist.json"
        original_hash = sha(self.reference.read_bytes())
        self.summary.write_text("No final model answer was available.\n")
        result = self.evaluate()
        contract = result["reference_contract"]
        self.assertEqual(contract["total_questions"], 60)
        self.assertEqual(contract["scorable_questions"], 46)
        self.assertEqual(contract["unresolved_questions"], 14)
        self.assertEqual(contract["unresolved_ids"], ["Q1", "Q2", "Q6", "Q10", "Q16", "Q19", "Q29", "Q30", "Q33", "Q39", "Q48", "Q53", "Q58", "Q60"])
        self.assertEqual(contract["review_status"], "draft_requires_independent_review")
        self.assertFalse(contract["independent_review_completed"])
        self.assertIsNone(result["score"])
        public = json.loads(self.questions.read_text())
        self.set_answers({"schema_version": 2, "case_id": public["case_id"], "answers": [
            {"question_id": q["id"], "status": "unknown"} for q in public["questions"]]})
        measured = self.evaluate("C", "measured")
        self.assertEqual(measured["score"]["question_counts"]["total"], 60)
        self.assertEqual(measured["score"]["scorable_questions"], 46)
        self.assertEqual(measured["score"]["question_counts"]["unevaluable"], 14)
        self.assertEqual(sha(self.reference.read_bytes()), original_hash)


if __name__ == "__main__":
    unittest.main()
