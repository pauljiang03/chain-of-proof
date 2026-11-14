"""Backend failures remain failed runs, including any saved certified work."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from agent import run
from checker.check import check
from checker.facts import open_source
from verifier.verify import verify_run


ROOT = Path(__file__).resolve().parent.parent
FACTS = ROOT / "fixtures/sample_facts.json"
REAL_POPEN = subprocess.Popen


class AgentFailures(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.output = self.root / "runs/probe"
        self.stdout = io.StringIO()

    def invoke(self, backend="claude-code", extra=(), scored=False):
        with patch.object(run, "ROOT", self.root), contextlib.redirect_stdout(self.stdout):
            return run.main(["--name", "probe", "--facts", str(FACTS),
                             "--backend", backend] + ([] if scored else ["--no-score"]) + list(extra))

    def saved(self):
        return json.loads((self.output / "run.json").read_text())

    def finalized(self):
        self.assertTrue({"run.json", "report.md", "summary.md", "results.json",
                         "case-profile.json", "prompt.md"}.issubset(
                             {p.name for p in self.output.iterdir()}))
        self.assertFalse(json.loads((self.output / "results.json").read_text())["evaluation"]["measured"])

    def local_cli(self, event, exit_code):
        program = "print(" + repr(json.dumps(event)) + ")\n" if event is not None else ""
        program += f"raise SystemExit({exit_code})\n"

        def fake_cli(_command, **kwargs):
            return REAL_POPEN([sys.executable, "-c", program], **kwargs)

        with patch("agent.run.subprocess.Popen", side_effect=fake_cli):
            return self.invoke()

    def test_success_event_and_zero_exit_succeed(self):
        self.assertEqual(self.local_cli({"type": "result", "subtype": "success", "result": "done"}, 0), 0)
        self.finalized()
        self.assertEqual(self.saved()["case"]["ended"], "success")
        self.assertEqual((self.output / "summary.md").read_text(), "done\n")

    def test_success_event_does_not_hide_nonzero_exit(self):
        self.assertEqual(self.local_cli({"type": "result", "subtype": "success", "result": "partial"}, 3), 1)
        self.finalized()
        meta = self.saved()["case"]
        self.assertEqual((meta["ended"], meta["exit_code"], meta["result_subtype"]),
                         ("process_error", 3, "success"))

    def test_error_result_with_nonzero_exit_fails(self):
        self.assertEqual(self.local_cli({"type": "result", "subtype": "error_during_execution",
                                         "is_error": True}, 1), 1)
        self.finalized()
        meta = self.saved()["case"]
        self.assertTrue(meta["is_error"])
        self.assertEqual(meta["result_subtype"], "error_during_execution")
        self.assertEqual(meta["exit_code"], 1)

    def test_error_flag_with_success_subtype_and_zero_exit_fails(self):
        self.assertEqual(self.local_cli({"type": "result", "subtype": "success", "is_error": True}, 0), 1)
        self.assertEqual(self.saved()["case"]["ended"], "result_error")

    def test_error_subtype_without_flag_and_zero_exit_fails(self):
        self.assertEqual(self.local_cli({"type": "result", "subtype": "error_during_execution"}, 0), 1)
        self.assertTrue(self.saved()["case"]["is_error"])

    def test_error_result_with_null_summary_still_finalizes(self):
        self.assertEqual(self.local_cli({"type": "result", "subtype": "error_during_execution",
                                         "is_error": True, "result": None}, 1), 1)
        self.finalized()
        self.assertEqual((self.output / "summary.md").read_text(), "\n")

    def test_missing_result_event_fails_even_with_zero_exit(self):
        self.assertEqual(self.local_cli(None, 0), 1)
        self.assertEqual(self.saved()["case"]["ended"], "no result event")

    def test_missing_executable_preserves_failure_artifacts_without_secret_text(self):
        with patch("agent.run.subprocess.Popen", side_effect=FileNotFoundError("SECRET-REQUEST-TOKEN")):
            self.assertEqual(self.invoke(), 1)
        self.finalized()
        meta = self.saved()["case"]
        self.assertEqual((meta["ended"], meta["error_type"]), ("backend_error", "FileNotFoundError"))
        self.assertTrue(meta["is_error"])
        self.assert_no_exception_payload()

    def test_missing_optional_dependency_is_finalized(self):
        with patch.object(run, "run_deepagents", side_effect=ModuleNotFoundError("SECRET-REQUEST-TOKEN")):
            self.assertEqual(self.invoke("deepagents"), 1)
        self.finalized()
        self.assertEqual(self.saved()["case"]["error_type"], "ModuleNotFoundError")
        self.assert_no_exception_payload()

    def test_runtime_provider_failure_is_finalized(self):
        with patch.object(run, "run_deepagents", side_effect=RuntimeError("SECRET-REQUEST-TOKEN")):
            self.assertEqual(self.invoke("deepagents"), 1)
        self.finalized()
        self.assertEqual(self.saved()["case"]["error_type"], "RuntimeError")
        self.assert_no_exception_payload()

    def test_optional_sdk_error_is_recognized_without_installing_it(self):
        class AnthropicError(Exception):
            pass

        class AuthenticationError(AnthropicError):
            pass

        sdk = types.ModuleType("anthropic")
        sdk.AnthropicError = AnthropicError
        with patch.dict(sys.modules, {"anthropic": sdk}), \
             patch.object(run, "run_deepagents", side_effect=AuthenticationError("SECRET-REQUEST-TOKEN")):
            self.assertEqual(self.invoke("deepagents"), 1)
        self.finalized()
        self.assertEqual(self.saved()["case"]["error_type"], "AuthenticationError")
        self.assert_no_exception_payload()

    def test_provider_failure_preserves_and_bundles_a_real_certificate(self):
        preserved = {}

        def save_then_fail(_model, run_dir, _facts, **kwargs):
            certificate = check({"searched": [3100]}, "A001", open_source(FACTS),
                                "Which search?", run_dir, proposer="test")
            self.assertEqual(certificate["status"], "verified")
            for name in ("A001.json", "A001.lean", "proposals.jsonl"):
                preserved[name] = (run_dir / name).read_bytes()
            raise RuntimeError("SECRET-REQUEST-TOKEN")

        with patch.object(run, "run_deepagents", side_effect=save_then_fail):
            self.assertEqual(self.invoke("deepagents"), 1)
        self.finalized()
        for name, value in preserved.items():
            self.assertEqual((self.output / name).read_bytes(), value)
        saved = self.saved()
        self.assertEqual(saved["stats"]["verified"], 1)
        self.assertEqual([f["finding_id"] for f in saved["findings"]], ["A001"])
        self.assertTrue(verify_run(saved, open_source(FACTS))["passed"])
        self.assertIn("A001", (self.output / "report.md").read_text())
        self.assert_no_exception_payload()

    def test_unexpected_programming_error_is_reraised_after_finalization(self):
        with patch.object(run, "run_deepagents", side_effect=TypeError("SECRET-REQUEST-TOKEN")), \
             self.assertRaises(TypeError):
            self.invoke("deepagents")
        self.finalized()
        self.assertEqual(self.saved()["case"]["error_type"], "TypeError")
        self.assert_no_exception_payload()

    def test_keyboard_interrupt_is_not_caught_as_backend_error(self):
        with patch.object(run, "run_deepagents", side_effect=KeyboardInterrupt), \
             self.assertRaises(KeyboardInterrupt):
            self.invoke("deepagents")

    def test_own_deadline_remains_an_ordinary_partial_run(self):
        meta = {"summary": "time reached", "turns": None, "tool_calls": 0,
                "seconds": 60, "ended": "time_limit", "exit_code": -9, "is_error": False}
        with patch.object(run, "run_claude_code", return_value=meta):
            self.assertEqual(self.invoke(), 0)
        self.finalized()
        self.assertEqual(self.saved()["case"]["ended"], "time_limit")

    def test_deadline_does_not_hide_an_observed_provider_error(self):
        meta = {"summary": "", "turns": None, "tool_calls": 0,
                "seconds": 60, "ended": "time_limit", "exit_code": -9, "is_error": True}
        with patch.object(run, "run_claude_code", return_value=meta):
            self.assertEqual(self.invoke(), 1)

    def gate_args(self, scored=False):
        labels = self.root / "gate.json"
        labels.write_text(json.dumps({"facts": {"search": {
            "kind": "webSearch", "obj": "sample data leakage methods"}}, "claims": [
                {"id": "false-usb", "label": False, "claim": {"usbConnected": ["search"]}}]}))
        args = ["--labeled-claims", str(labels)]
        if scored:
            public = self.root / "public.json"
            reference = self.root / "reference.json"
            case = "nist-cfreds-data-leakage"
            public.write_text(json.dumps({"schema_version": 2, "case_id": case, "questions": [
                {"id": "Q16", "prompt": "Which search?", "answer_schema": {}}]}))
            reference.write_text(json.dumps({"schema_version": 2, "case_id": case, "questions": [
                {"id": "Q16", "prompt": "Which search?", "expected": {"searches": [
                    {"timestamp": "2015-03-23T13:56:40Z", "keyword": "sample data leakage methods",
                     "browser": "(none)"}]}}]}))
            args += ["--questions", str(public), "--reference", str(reference), "--adapter", "nist"]
        return args

    def save_partial(self, _model, run_dir, _facts, **kwargs):
        certificate = check({"searched": [3100]}, "A001", open_source(FACTS),
                            "Which search?", run_dir, proposer="test")
        self.assertEqual(certificate["status"], "verified")
        raise RuntimeError("SECRET-REQUEST-TOKEN")

    def test_gate_error_after_partial_backend_failure_preserves_run_and_scores(self):
        def failing_gate(*args, **kwargs):
            self.assertTrue((self.output / "report.md").exists())
            self.assertEqual(self.saved()["case"]["ended"], "backend_error")
            raise RuntimeError("SECRET-REQUEST-TOKEN")

        with patch.object(run, "run_deepagents", side_effect=self.save_partial), \
             patch.object(run.gate, "measure", side_effect=failing_gate):
            self.assertEqual(self.invoke("deepagents", self.gate_args(scored=True), scored=True), 1)
        self.assertEqual(self.saved()["case"]["gate_error_type"], "RuntimeError")
        self.assertTrue(json.loads((self.output / "verification.json").read_text())["passed"])
        result = json.loads((self.output / "results.json").read_text())
        self.assertTrue(result["evaluation"]["measured"])
        self.assertEqual(result["question_counts"]["fully_correct"], 1)
        self.assertFalse(result["gate_regression"]["measured"])
        self.assertNotIn("all_as_expected", result["gate_regression"])
        self.assertEqual([f["finding_id"] for f in self.saved()["findings"]], ["A001"])
        self.assert_no_exception_payload()

    def test_gate_error_does_not_hide_failed_certificate_verification(self):
        def save_invalid(*args, **kwargs):
            try:
                self.save_partial(*args, **kwargs)
            except RuntimeError:
                path = self.output / "A001.json"
                certificate = json.loads(path.read_text())
                certificate["cited_facts"][0]["obj_text"] = "forged search"
                path.write_text(json.dumps(certificate))
                raise

        with patch.object(run, "run_deepagents", side_effect=save_invalid), \
             patch.object(run.gate, "measure", side_effect=RuntimeError("SECRET-REQUEST-TOKEN")), \
             contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            self.invoke("deepagents", self.gate_args(scored=True), scored=True)
        self.assertEqual(error.exception.code, 2)
        self.assertEqual(self.saved()["case"]["gate_error_type"], "RuntimeError")
        self.assertFalse(json.loads((self.output / "verification.json").read_text())["passed"])
        self.assertFalse((self.output / "results.json").exists())
        self.assertFalse((self.output / "answers.json").exists())
        self.assertTrue((self.output / "report.md").exists())
        self.assert_no_exception_payload()

    def test_gate_subprocess_failure_returns_nonzero_after_successful_backend(self):
        meta = {"summary": "done", "turns": 1, "tool_calls": 0, "seconds": 0, "ended": "success"}
        failure = subprocess.CalledProcessError(1, ["SECRET-REQUEST-TOKEN"])
        with patch.object(run, "run_deepagents", return_value=meta), \
             patch.object(run.gate, "measure", side_effect=failure):
            self.assertEqual(self.invoke("deepagents", self.gate_args()), 1)
        self.finalized()
        self.assertEqual(self.saved()["case"]["gate_error_type"], "CalledProcessError")
        self.assertFalse(json.loads((self.output / "results.json").read_text())["gate_regression"]["measured"])
        self.assert_no_exception_payload()

    def test_normal_gate_is_measured_without_changing_investigation_findings(self):
        meta = {"summary": "done", "turns": 1, "tool_calls": 0, "seconds": 0, "ended": "success"}
        with patch.object(run, "run_deepagents", return_value=meta):
            self.assertEqual(self.invoke("deepagents", self.gate_args()), 0)
        self.finalized()
        result = json.loads((self.output / "results.json").read_text())["gate_regression"]
        self.assertTrue(result["measured"])
        self.assertTrue(result["all_as_expected"])
        self.assertEqual(result["false_claims_rejected"], 1)
        self.assertEqual(self.saved()["findings"], [])
        self.assertEqual(self.saved()["stats"]["proposals"], 0)
        self.assertNotIn("gate_error_type", self.saved()["case"])

    def test_unexpected_gate_error_is_reraised_after_artifacts_are_saved(self):
        meta = {"summary": "done", "turns": 1, "tool_calls": 0, "seconds": 0, "ended": "success"}
        with patch.object(run, "run_deepagents", return_value=meta), \
             patch.object(run.gate, "measure", side_effect=TypeError("SECRET-REQUEST-TOKEN")), \
             self.assertRaises(TypeError):
            self.invoke("deepagents", self.gate_args())
        self.finalized()
        self.assertEqual(self.saved()["case"]["gate_error_type"], "TypeError")
        self.assert_no_exception_payload()

    def assert_no_exception_payload(self):
        for path in self.output.iterdir():
            if path.is_file():
                self.assertNotIn("SECRET-REQUEST-TOKEN", path.read_text(), path.name)
        self.assertNotIn("SECRET-REQUEST-TOKEN", self.stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
