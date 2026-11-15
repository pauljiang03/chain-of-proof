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

from eval import benchmark


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

    def write(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value) + "\n")
        return path

    def args(self, output):
        return ["--reference", str(self.reference), "--answers", str(self.answers), "--out", str(output)]

    def invoke(self, output, extra=()):
        return subprocess.run([sys.executable, "-m", "eval.benchmark", *self.args(output), *extra],
                              cwd=ROOT, capture_output=True, text=True, timeout=30)

    def assert_cli_error(self, result):
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("error:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_new_score_preserves_values_and_input_hashes(self):
        output = self.root / "new" / "results.json"
        originals = {p: p.read_bytes() for p in (self.reference, self.answers)}
        result = self.invoke(output)
        self.assertEqual(result.returncode, 0, result.stderr)
        saved = json.loads(output.read_text())
        self.assertTrue(saved["perfect_submission"])
        self.assertEqual(saved["question_counts"]["fully_correct"], 1)
        for name, path in (("reference", self.reference), ("answers", self.answers)):
            self.assertEqual(saved["inputs"][name]["sha256"], hashlib.sha256(originals[path]).hexdigest())
            self.assertEqual(path.read_bytes(), originals[path])

    def test_existing_results_are_preserved(self):
        output = self.root / "existing.json"
        output.write_bytes(b"previous run\n")
        result = self.invoke(output)
        self.assert_cli_error(result)
        self.assertIn("refusing to overwrite", result.stderr)
        self.assertEqual(output.read_bytes(), b"previous run\n")

    def test_input_paths_and_hardlink_aliases_are_preserved(self):
        for source in (self.reference, self.answers):
            before = source.read_bytes()
            alias = self.root / (source.name + ".alias")
            os.link(source, alias)
            for output in (source, alias):
                with self.subTest(output=output.name):
                    self.assert_cli_error(self.invoke(output))
                    self.assertEqual(source.read_bytes(), before)
                    self.assertEqual(alias.read_bytes(), before)

    def test_symlink_outputs_never_modify_their_targets(self):
        for existing in (True, False):
            with self.subTest(existing_target=existing):
                target = self.root / f"target-{existing}.json"
                if existing:
                    target.write_bytes(b"keep target\n")
                link = target.with_suffix(".link")
                link.symlink_to(target)
                self.assert_cli_error(self.invoke(link))
                self.assertTrue(link.is_symlink())
                if existing:
                    self.assertEqual(target.read_bytes(), b"keep target\n")
                else:
                    self.assertFalse(target.exists())

    def test_output_collision_during_write_preserves_the_other_writer(self):
        original_open = Path.open
        for symlink in (False, True):
            with self.subTest(symlink=symlink):
                output = self.root / f"race-{symlink}.json"
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
                    benchmark.main(self.args(output))
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
        self.assert_cli_error(self.invoke(parent / "result.json"))
        self.assertEqual(parent.read_text(), "keep parent")

    def test_missing_inputs_do_not_create_an_output(self):
        for flag in ("--reference", "--answers"):
            with self.subTest(flag=flag):
                output = self.root / "missing-output.json"
                self.assert_cli_error(self.invoke(output, [flag, str(self.root / "missing")]))
                self.assertFalse(output.exists())

    def test_malformed_json_or_schema_does_not_create_an_output(self):
        for content in ("{invalid", "[]", '{"schema_version": 2}'):
            malformed = self.root / "malformed.json"
            malformed.write_text(content)
            for flag in ("--reference", "--answers"):
                with self.subTest(flag=flag, content=content):
                    output = self.root / "malformed-output.json"
                    self.assert_cli_error(self.invoke(output, [flag, str(malformed)]))
                    self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
