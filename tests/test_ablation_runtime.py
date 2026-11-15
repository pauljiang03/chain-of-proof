"""Offline tests of matched subagent sessions, transport and immutable finalization."""
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from agent.audit import verify_audit
from comparison.ablation import runtime
from comparison.ablation.mcp_server import make_workbench
from comparison.ablation.prompt import GATE

ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.facts = self.root / "facts.json"
        self.facts.write_text(json.dumps({"strings": {"1": "fixture device", "2": "fixture volume"},
            "facts": [{"id": 1, "kind": "usbInsert", "t": 0, "res": 0,
                       "obj": 1, "aux": 2, "prov": {"artifact": "fixture"}}]}))
        self.profile = self.root / "profile.json"
        self.profile.write_text(json.dumps({"name": "Fixture case", "brief": "Examine public records.",
                                           "questions": ["Device?"], "case_id": "fixture"}))
        self.questions = self.root / "questions.json"
        self.questions.write_text(json.dumps({"schema_version": 2, "case_id": "fixture", "questions": [
            {"id": "Q1", "prompt": "Which device?", "answer_schema": {"type": "string"}}]}))
        self.summary = self.root / "raw-model-final.txt"
        self.summary.write_bytes(b'Unverified direct answer.\n```json\n{"schema_version":2,"case_id":"fixture",'
            b'"answers":[{"question_id":"Q1","status":"unknown"}]}\n```  \n\n')

    def init(self, arm, name=None):
        out = self.root / (name or arm)
        runtime.init_session(arm=arm, facts=self.facts, case_profile=self.profile,
                             questions=self.questions, out=out)
        return out

    def cli(self, *argv):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = runtime.main(list(map(str, argv)))
        return code, stdout.getvalue(), stderr.getvalue()

    def rows(self, run, name):
        return [json.loads(line) for line in (run / name).read_text().splitlines()]

    def test_matched_public_prompt_only_gate_paragraph_differs(self):
        a, c = self.init("A"), self.init("C")
        self.assertEqual((a / "prompt.md").read_text().replace(GATE["A"], "<GATE>"),
                         (c / "prompt.md").read_text().replace(GATE["C"], "<GATE>"))
        self.assertIn('"question_id": "Q1"', (a / "prompt.md").read_text())
        self.assertIn("not an operating-system sandbox", (a / "prompt.md").read_text())
        metadata = json.loads((a / "session.json").read_text())
        self.assertEqual(metadata["requested_model"], "gpt-6.1-sol")
        self.assertEqual(metadata["facts"]["sha256"], runtime._binding(self.facts)["sha256"])
        self.assertEqual((a / "case-profile.json").read_bytes(), self.profile.read_bytes())
        self.assertEqual((a / "questions.json").read_bytes(), self.questions.read_bytes())

    def test_init_refuses_private_contract_fields_and_existing_outputs(self):
        run = self.init("A")
        before = (run / "session.json").read_bytes()
        with self.assertRaises(FileExistsError):
            self.init("A")
        self.assertEqual((run / "session.json").read_bytes(), before)
        public = json.loads(self.questions.read_text())
        public["questions"][0]["expected"] = "secret"
        self.questions.write_text(json.dumps(public))
        with self.assertRaisesRegex(ValueError, "private"):
            self.init("C")
        self.assertFalse((self.root / "C").exists())

    def test_cli_receipts_restart_without_checker_and_preserve_batch_positions(self):
        run = self.init("A")
        with patch("checker.check.check", side_effect=AssertionError("active checker")), \
             patch("checker.claims.parse", side_effect=AssertionError("semantic parser")), \
             patch("agent.history.validate_revision", side_effect=AssertionError("revision check")):
            for claim in ('{"usbConnected":[1]}', '{"usbConnected":[1]}', '{"imaginary":"raw string"}'):
                code, out, err = self.cli("tool", "--run", run, "check", "--question", "Q1", "--claim", claim)
                self.assertEqual(code, 0, err)
                self.assertEqual(json.loads(out)["status"], "unverified")
            code, out, err = self.cli("tool", "--run", run, "check", "--question", "Q1",
                "--claim", '{"x":null}', "--claim", '{"both":[false]}', "--revises", "future-id")
            self.assertEqual(code, 0, err)
            self.assertEqual([r["candidate_id"] for r in json.loads(out)], ["P000004", "P000005"])
        rows = self.rows(run, "candidates.jsonl")
        self.assertEqual([r["candidate_id"] for r in rows], [f"P{n:06d}" for n in range(1, 6)])
        self.assertEqual(rows[0]["claim"], rows[1]["claim"])
        self.assertEqual(rows[2]["claim"], {"imaginary": "raw string"})
        self.assertEqual(rows[-1]["revises"], "future-id")
        self.assertEqual(self.rows(run, "bridge-calls.jsonl")[-1]["batch"], [
            {"position": 1, "candidate_id": "P000004", "finding_id": None},
            {"position": 2, "candidate_id": "P000005", "finding_id": None}])
        self.assertTrue(verify_audit(run / "audit.jsonl")["passed"])
        self.assertFalse((run / "proposals.jsonl").exists())

    def test_shared_structural_errors_do_not_partially_submit_batches(self):
        for arm in ("A", "C"):
            run = self.init(arm)
            invalid = [{"question": "Q1", "claims": [{"usbConnected": [1]}, "{}"]},
                       {"question": "Q1", "claims": []},
                       {"question": "Q1", "claim": "{}"},
                       {"question": "Q1", "claim": {}, "revises": 1}]
            with patch("checker.check.check", side_effect=AssertionError("checker called")):
                for args in invalid:
                    with self.assertRaises(ValueError):
                        runtime.call_tool(run, "check", args)
            self.assertFalse((run / "proposals.jsonl").exists())
            if arm == "A":
                self.assertEqual((run / "candidates.jsonl").read_bytes(), b"")

    def test_same_read_tools_and_sql_mutation_refusal(self):
        a, c = self.init("A"), self.init("C")
        for tool, args in (("forms", {}), ("sql", {"query": "SELECT * FROM facts"}), ("fact", {"id": 1})):
            self.assertEqual(runtime.call_tool(a, tool, args), runtime.call_tool(c, tool, args))
        for run in (a, c):
            self.assertIn("error", runtime.call_tool(run, "sql", {"query": "DELETE FROM facts"}))
            self.assertEqual(runtime.call_tool(run, "sql", {"query": "SELECT count(*) FROM facts"})["rows"], [[1]])
            with self.assertRaises(ValueError):
                runtime.call_tool(run, "conclude", {})
            self.assertFalse((run / "conclusions.jsonl").exists())

    def test_persistent_session_loads_once_and_does_not_audit_transport(self):
        run = self.init("A")
        requests = ["{invalid}", '{"tool":"sql","arguments":{"query":"SELECT id FROM facts"}}',
                    '{"tool":"check","arguments":{"question":"Q1","claim":{"bad":[]}}}',
                    '{"tool":"check","arguments":{"question":"Q1","claim":{"bad":[]}}}',
                    '{"tool":"conclude"}', '{"tool":"close"}', '{"tool":"forms"}']
        stdout = io.StringIO()
        with patch("comparison.ablation.runtime.make_workbench", wraps=make_workbench) as create:
            runtime.serve_session(run, stdin=io.StringIO("\n".join(requests)), stdout=stdout)
        self.assertEqual(create.call_count, 1)
        responses = [json.loads(line) for line in stdout.getvalue().splitlines()]
        self.assertEqual(responses[0], {"status": "ready", "arm": "A"})
        self.assertFalse(responses[1]["ok"])
        self.assertEqual(responses[2]["result"]["rows"], [[1]])
        self.assertEqual(responses[3]["result"]["candidate_id"], "P000001")
        self.assertEqual(responses[4]["result"]["candidate_id"], "P000002")
        self.assertFalse(responses[5]["ok"])
        self.assertEqual(responses[-1], {"status": "closed"})
        self.assertEqual([row["tool"] for row in self.rows(run, "audit.jsonl")], ["sql", "check", "check"])

    def test_separate_processes_restart_ids_and_exclude_active_finalizer(self):
        run = self.init("A")
        prefix = [PYTHON, "-m", "comparison.ablation.runtime"]
        for expected in ("P000001", "P000002"):
            result = subprocess.run(prefix + ["tool", "--run", str(run), "check", "--question", "Q1",
                "--claim", '{"bad":[]}'], cwd=ROOT, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["candidate_id"], expected)
        process = subprocess.Popen(prefix + ["session", "--run", str(run)], cwd=ROOT,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, bufsize=1)
        try:
            self.assertEqual(json.loads(process.stdout.readline())["status"], "ready")
            with self.assertRaisesRegex(RuntimeError, "active bridge"):
                runtime.call_tool(run, "forms", {})
            with self.assertRaisesRegex(RuntimeError, "active bridge"):
                runtime.finalize_session(run, summary=self.summary, status="completed")
            self.assertFalse((run / ".finalizing").exists())
            output, error = process.communicate('{"tool":"check","arguments":{"question":"Q1",'
                '"claim":{"bad":[]}}}\n{"tool":"close"}\n', timeout=30)
            self.assertEqual(process.returncode, 0, error)
            self.assertEqual(json.loads(output.splitlines()[0])["result"]["candidate_id"], "P000003")
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate(timeout=10)
        self.assertTrue(verify_audit(run / "audit.jsonl")["passed"])

    def test_final_a_preserves_exact_summary_and_seals_unverified_only(self):
        run = self.init("A")
        runtime.call_tool(run, "check", {"question": "Q1", "claim": {"wrong": [1]}})
        with patch("checker.export.bundle", side_effect=AssertionError("verified export in A")), \
             patch("checker.check.check", side_effect=AssertionError("checker in A")), \
             patch("verifier.verify.verify_run", side_effect=AssertionError("replay in A")):
            result = runtime.finalize_session(run, summary=self.summary, status="time_limit", elapsed_seconds=5.25)
        self.assertEqual((run / "summary.md").read_bytes(), self.summary.read_bytes())
        self.assertEqual(result["claim_status"], "unverified")
        self.assertEqual(result["candidates"], 1)
        self.assertIsNone(result["model_usage"])
        self.assertIsNone(result["immutable_model_revision"])
        self.assertIsNone(result["observed_model_ids"])
        self.assertEqual(result["elapsed_seconds"], 5.25)
        self.assertFalse((run / "run.json").exists())
        self.assertFalse((run / "report.md").exists())
        before = (run / "seal.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "frozen"):
            runtime.call_tool(run, "forms", {})
        with self.assertRaisesRegex(ValueError, "frozen"):
            runtime.finalize_session(run, summary=self.summary, status="completed")
        self.assertEqual((run / "seal.json").read_bytes(), before)

    def test_startup_failure_with_zero_tools_is_preserved(self):
        run = self.init("A")
        self.summary.write_bytes(b"")
        result = runtime.finalize_session(run, summary=self.summary, status="failed")
        self.assertEqual(result["candidates"], 0)
        self.assertEqual(result["status"], "failed")
        self.assertIsNone(result["elapsed_seconds"])
        self.assertEqual((run / "summary.md").read_bytes(), b"")

    def test_c_real_gate_ids_survive_restarts_and_certificates_replay(self):
        run = self.init("C")
        first = runtime.call_tool(run, "check", {"question": "Q1", "claim": {"usbConnected": [1]}})
        second = runtime.call_tool(run, "check", {"question": "Q1", "claim": {"searched": [1]}})
        self.assertEqual((first["finding_id"], first["status"]), ("A001", "verified"))
        self.assertEqual((second["finding_id"], second["status"]), ("A002", "rejected"))
        duplicate = runtime.call_tool(run, "check", {"question": "Q1", "claim": {"usbConnected": [1]}})
        self.assertEqual(duplicate["finding_id"], "A001")
        (run / "A001.lean").write_text("-- unrelated stored proof must not appear in the report\n")
        result = runtime.finalize_session(run, summary=self.summary, status="completed", elapsed_seconds=1)
        self.assertEqual(result["certificate_replay"]["checked"], 1)
        self.assertTrue(result["certificate_replay"]["passed"])
        data = json.loads((run / "run.json").read_text())
        self.assertEqual(data["case"]["ended"], "success")
        self.assertEqual(data["stats"]["proposals"], 2)
        self.assertEqual(data["audit"]["status"], "valid")
        self.assertIn("theorem verified", data["findings"][0]["lean"])
        self.assertNotIn("unrelated stored proof", data["findings"][0]["lean"])
        self.assertIn("A001", (run / "report.md").read_text())
        self.assertFalse((run / "candidates.jsonl").exists())

    def test_c_replay_failure_is_preserved_as_failed_trial_and_nonzero_cli(self):
        run = self.init("C")
        failed = {"passed": False, "checked": 1, "verified": 0, "failed": 1,
                  "findings": [{"finding_id": "A001", "problems": ["synthetic replay failure"]}]}
        with patch("verifier.verify.verify_run", return_value=failed):
            code, out, err = self.cli("finalize", "--run", run, "--summary", self.summary,
                                      "--status", "completed")
        self.assertEqual(code, 1, err)
        metadata = json.loads(out)
        self.assertEqual(metadata["status"], "failed")
        self.assertEqual(metadata["investigator_status"], "completed")
        self.assertEqual(metadata["failure_reason"], "certificate_replay_failed")
        self.assertEqual(json.loads((run / "verification.json").read_text()), failed)
        self.assertEqual((run / "summary.md").read_bytes(), self.summary.read_bytes())
        self.assertFalse((run / "report.md").exists())
        self.assertTrue((run / "trial.json").is_file())

    def test_changed_public_inputs_or_facts_refused_before_dispatch(self):
        run = self.init("C")
        with (run / "prompt.md").open("a") as stream:
            stream.write("changed")
        with patch("comparison.ablation.runtime.make_workbench") as create:
            code, _, err = self.cli("tool", "--run", run, "forms")
        self.assertEqual(code, 2)
        self.assertIn("public session input changed", err)
        create.assert_not_called()
        run = self.init("A")
        self.facts.write_text(self.facts.read_text() + "\n")
        with self.assertRaisesRegex(ValueError, "facts changed"):
            runtime.finalize_session(run, summary=self.summary, status="completed")
        self.assertFalse((run / "seal.json").exists())

    def test_symlink_inputs_and_lock_are_refused(self):
        run = self.init("A")
        (run / ".bridge.lock").symlink_to(self.root / "missing-lock-target")
        code, _, _ = self.cli("tool", "--run", run, "forms")
        self.assertEqual(code, 2)
        self.assertFalse((self.root / "missing-lock-target").exists())
        (run / ".bridge.lock").unlink()
        (run / "questions.json").unlink()
        (run / "questions.json").symlink_to(self.questions)
        with self.assertRaises(OSError):
            runtime.call_tool(run, "forms", {})

    def test_cli_strict_json_and_terminal_values(self):
        run = self.init("A")
        for raw in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":1e999}', '"{}"', '[{}]'):
            code, _, err = self.cli("tool", "--run", run, "check", "--question", "Q1", "--claim", raw)
            self.assertEqual(code, 2, raw)
            self.assertNotIn("Traceback", err)
        for value in (-1, float("inf"), float("nan"), True):
            with self.assertRaises(ValueError):
                runtime.finalize_session(run, summary=self.summary, status="completed", elapsed_seconds=value)
        self.assertFalse((run / ".finalizing").exists())

    def test_inflight_finalization_input_mutation_never_publishes_trial(self):
        run = self.init("C")
        def mutate(*_):
            self.facts.write_text(self.facts.read_text() + "\n")
            return {"passed": True, "checked": 0, "verified": 0, "failed": 0, "findings": []}
        with patch("verifier.verify.verify_run", side_effect=mutate), self.assertRaisesRegex(ValueError, "facts changed"):
            runtime.finalize_session(run, summary=self.summary, status="completed")
        self.assertFalse((run / "trial.json").exists())
        self.assertTrue((run / ".finalizing").exists())
        self.assertEqual((run / "summary.md").read_bytes(), self.summary.read_bytes())


if __name__ == "__main__":
    unittest.main()
