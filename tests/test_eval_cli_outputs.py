"""Evaluation CLI failures preserve inputs and earlier outputs, including races."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from eval import benchmark, submission


ROOT = Path(__file__).resolve().parent.parent


class EvaluationCLIOutputs(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.reference = self.write("reference.json", {
            "schema_version": 2, "case_id": "cli-fixture",
            "questions": [{"id": "Q1", "prompt": "What is recorded?", "expected": False}]})
        self.answer_value = {"schema_version": 2, "case_id": "cli-fixture",
                             "answers": [{"question_id": "Q1", "status": "answered", "answer": False}]}
        self.answers = self.write("answers.json", self.answer_value)
        self.questions = self.write("questions.json", {
            "schema_version": 2, "case_id": "cli-fixture",
            "questions": [{"id": "Q1", "prompt": "What is recorded?", "answer_schema": {}}]})
        self.report = self.root / "report.md"
        self.report.write_text("```json\n" + self.answers.read_text() + "```\n")

    def write(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value) + "\n")
        return path

    def args(self, module, output):
        inputs = (["--reference", str(self.reference), "--answers", str(self.answers)]
                  if module == "eval.benchmark" else
                  ["--report", str(self.report), "--questions", str(self.questions)])
        return inputs + ["--out", str(output)]

    def invoke(self, module, output, extra=()):
        return subprocess.run([sys.executable, "-m", module, *self.args(module, output), *extra],
                              cwd=ROOT, capture_output=True, text=True, timeout=30)

    def assert_cli_error(self, result):
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("error:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_new_score_preserves_values_and_input_hashes(self):
        output = self.root / "new" / "results.json"
        originals = {p: p.read_bytes() for p in (self.reference, self.answers)}
        result = self.invoke("eval.benchmark", output)
        self.assertEqual(result.returncode, 0, result.stderr)
        saved = json.loads(output.read_text())
        self.assertTrue(saved["perfect_submission"])
        self.assertEqual(saved["question_counts"]["fully_correct"], 1)
        for name, path in (("reference", self.reference), ("answers", self.answers)):
            self.assertEqual(saved["inputs"][name]["sha256"], hashlib.sha256(originals[path]).hexdigest())
            self.assertEqual(path.read_bytes(), originals[path])

    def test_new_submission_preserves_typed_answers_and_report_hash(self):
        output = self.root / "new" / "submission.json"
        before = self.report.read_bytes()
        result = self.invoke("eval.submission", output)
        self.assertEqual(result.returncode, 0, result.stderr)
        saved = json.loads(output.read_text())
        self.assertEqual(saved["answers"], self.answer_value["answers"])
        self.assertEqual(saved["submission_origin"]["report_sha256"], hashlib.sha256(before).hexdigest())
        self.assertEqual(self.report.read_bytes(), before)

    def test_existing_results_are_preserved(self):
        output = self.root / "existing.json"
        output.write_bytes(b"previous run\n")
        for module in ("eval.benchmark", "eval.submission"):
            with self.subTest(module=module):
                result = self.invoke(module, output)
                self.assert_cli_error(result)
                self.assertIn("refusing to overwrite", result.stderr)
                self.assertEqual(output.read_bytes(), b"previous run\n")

    def test_input_paths_and_hardlink_aliases_are_preserved(self):
        for module, paths in (("eval.benchmark", (self.reference, self.answers)),
                              ("eval.submission", (self.report, self.questions))):
            for source in paths:
                before = source.read_bytes()
                alias = self.root / (source.name + ".alias")
                os.link(source, alias)
                for output in (source, alias):
                    with self.subTest(module=module, output=output.name):
                        self.assert_cli_error(self.invoke(module, output))
                        self.assertEqual(source.read_bytes(), before)
                        self.assertEqual(alias.read_bytes(), before)

    def test_symlink_outputs_never_modify_their_targets(self):
        for module in ("eval.benchmark", "eval.submission"):
            for existing in (True, False):
                with self.subTest(module=module, existing_target=existing):
                    target = self.root / f"{module}-{existing}.json"
                    if existing:
                        target.write_bytes(b"keep target\n")
                    link = target.with_suffix(".link")
                    link.symlink_to(target)
                    self.assert_cli_error(self.invoke(module, link))
                    self.assertTrue(link.is_symlink())
                    if existing:
                        self.assertEqual(target.read_bytes(), b"keep target\n")
                    else:
                        self.assertFalse(target.exists())

    def test_output_collision_during_write_preserves_the_other_writer(self):
        original_open = Path.open
        for module, main in (("eval.benchmark", benchmark.main), ("eval.submission", submission.main)):
            for symlink in (False, True):
                with self.subTest(module=module, symlink=symlink):
                    output = self.root / f"race-{module}-{symlink}.json"
                    target = output.with_suffix(".target")

                    def competing_writer(path, mode="r", *args, **kwargs):
                        if path == output and mode == "x":
                            if symlink:
                                path.symlink_to(target)
                            else:
                                with original_open(path, "x") as stream:
                                    stream.write("other writer\n")
                        return original_open(path, mode, *args, **kwargs)

                    with patch.object(Path, "open", competing_writer), \
                         contextlib.redirect_stdout(io.StringIO()) as stdout, \
                         contextlib.redirect_stderr(io.StringIO()) as stderr, \
                         self.assertRaises(SystemExit) as raised:
                        main(self.args(module, output))
                    self.assertEqual(raised.exception.code, 2)
                    self.assertEqual(stdout.getvalue(), "")
                    self.assertNotIn("Traceback", stderr.getvalue())
                    if symlink:
                        self.assertTrue(output.is_symlink())
                        self.assertFalse(target.exists())
                    else:
                        self.assertEqual(output.read_text(), "other writer\n")

    def test_output_parent_failure_is_a_clean_cli_error(self):
        parent = self.root / "not-a-directory"
        parent.write_text("keep parent")
        for module in ("eval.benchmark", "eval.submission"):
            with self.subTest(module=module):
                self.assert_cli_error(self.invoke(module, parent / "result.json"))
                self.assertEqual(parent.read_text(), "keep parent")

    def test_missing_inputs_do_not_create_an_output(self):
        for module, flags in (("eval.benchmark", ("--reference", "--answers")),
                              ("eval.submission", ("--report", "--questions"))):
            for flag in flags:
                with self.subTest(module=module, flag=flag):
                    output = self.root / "missing-output.json"
                    self.assert_cli_error(self.invoke(module, output, [flag, str(self.root / "missing")]))
                    self.assertFalse(output.exists())

    def test_malformed_json_or_schema_does_not_create_an_output(self):
        for content in ("{invalid", "[]", '{"schema_version": 2}'):
            malformed = self.root / "malformed.json"
            malformed.write_text(content)
            for module, flags in (("eval.benchmark", ("--reference", "--answers")),
                                  ("eval.submission", ("--questions",))):
                for flag in flags:
                    with self.subTest(module=module, flag=flag, content=content):
                        output = self.root / "malformed-output.json"
                        self.assert_cli_error(self.invoke(module, output, [flag, str(malformed)]))
                        self.assertFalse(output.exists())

    def test_submission_extraction_errors_are_clean_and_do_not_create_output(self):
        for content in ("Only prose", "```json\n{invalid\n```\n", self.report.read_text() * 2,
                        '```json\n{"schema_version": 2, "case_id": "wrong", "answers": []}\n```\n'):
            with self.subTest(content=content):
                self.report.write_text(content)
                output = self.root / "invalid-submission.json"
                self.assert_cli_error(self.invoke("eval.submission", output))
                self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
