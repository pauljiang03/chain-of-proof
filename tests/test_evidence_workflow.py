"""The audit, diagnostics, revision, citation and bundle paths work together."""
import json
import hashlib
import importlib.util
import os
from pathlib import Path
import tempfile
import socket
import unittest
from unittest.mock import patch

from agent import mcp_server
from agent.audit import verify_audit
from agent.tools import Workbench
from agent.run import run_deepagents
from checker import export, report
from verifier.verify import verify_run
from verifier.package import build_package, verify_package


ROOT = Path(__file__).resolve().parent.parent
FACTS = ROOT / "fixtures/sample_facts.json"


class EvidenceWorkflow(unittest.TestCase):
    def test_explicit_revision_is_a_new_proof_and_history_does_not_invent_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            bench = Workbench(FACTS, directory, "synthetic workflow test")
            bench.fact(3100)
            refused = bench.check("Q1", {"usbConnected": [3100]})
            self.assertEqual(refused["proof_gap"]["requirements"][0]["category"], "wrong_record_type")
            changed = json.loads(mcp_server.call(bench, "check", {
                "question": "Q1", "claims": [{"searched": [3100]}],
                "revises": refused["finding_id"]}))[0]
            self.assertEqual(changed["status"], "verified")
            self.assertNotEqual(changed["finding_id"], refused["finding_id"])
            repeated = bench.check("Q1", {"searched": [3100]})
            self.assertIn("already proposed", repeated["note"])
            bad = bench.check("Q1", {"searched": [3100]}, revises="A999")
            self.assertEqual(bad["status"], "rejected")
            self.assertNotIn("finding_id", bad)
            unchanged = bench.check("Q1", {"searched": [3100]}, revises=changed["finding_id"])
            self.assertEqual(unchanged["status"], "rejected")
            self.assertIn("unchanged", unchanged["reason"])
            proposals = [json.loads(line) for line in (directory / "proposals.jsonl").read_text().splitlines()]
            self.assertEqual(len(proposals), 2)
            self.assertNotIn("revises", proposals[1])
            self.assertTrue(verify_audit(directory / "audit.jsonl")["passed"])
            events = [json.loads(line) for line in (directory / "audit.jsonl").read_text().splitlines()]
            self.assertEqual(len(events), 6)
            self.assertEqual(events[2]["arguments"]["revises"], refused["finding_id"])
            run = export.bundle(directory, "Synthetic fixture workflow")
            self.assertTrue(verify_run(run, bench.source)["passed"])
            self.assertEqual(run["stats"]["verified"], 1)
            text = report.render(run)
            self.assertIn("Not established / further evidence needed", text)
            self.assertIn("#evidence-f1-r1", text)
            self.assertIn("wrong", text)
            (directory / "run.json").write_text(json.dumps(run))
            package = directory / "portable"
            build_package(directory / "run.json", FACTS, package)
            anchor = hashlib.sha256((package / "manifest.json").read_bytes()).hexdigest()
            verified = verify_package(package, expected_manifest_sha256=anchor)
            self.assertTrue(verified["passed"], verified)
            self.assertEqual(verified["audit"]["count"], 6)
            self.assertIn("Recorded claim attempts", (package / "report.md").read_text())
            with (package / "audit.jsonl").open("a") as stream:
                stream.write("{}\n")
            tampered = verify_package(package, expected_manifest_sha256=anchor)
            self.assertFalse(tampered["passed"])
            self.assertTrue(any("audit.jsonl" in problem for problem in tampered["problems"]))

    def test_ordinary_duplicate_and_explicit_new_revision_remain_distinct(self):
        with tempfile.TemporaryDirectory() as tmp:
            bench = Workbench(FACTS, tmp)
            original = bench.check("Q1", {"searched": [3100]})
            wrong = bench.check("Q1", {"usbConnected": [3100]})
            revised = bench.check("Q1", {"searched": [3100]}, revises=wrong["finding_id"])
            self.assertEqual(revised["status"], "verified")
            self.assertNotEqual(revised["finding_id"], original["finding_id"])
            self.assertNotIn("already proposed", revised.get("note", ""))

    @unittest.skipUnless(importlib.util.find_spec("deepagents") is not None,
                         "optional API graph dependencies are not installed")
    def test_real_api_graph_passes_explicit_revision_and_logs_both_attempts_offline(self):
        from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
        from langchain_core.messages import AIMessage

        class OfflineModel(FakeMessagesListChatModel):
            def bind_tools(self, tools, **kwargs):
                return self

        model = OfflineModel(responses=[
            AIMessage(content="", tool_calls=[{"name": "check", "id": "bad", "args": {
                "question": "Q1", "claims": [{"usbConnected": [3100]}]}}]),
            AIMessage(content="", tool_calls=[{"name": "check", "id": "repair", "args": {
                "question": "Q1", "claims": [{"searched": [3100]}], "revises": "A001"}}]),
            AIMessage(content="offline fixture complete")])
        with tempfile.TemporaryDirectory() as tmp, \
             patch.dict(os.environ, {"LANGSMITH_TRACING": "false", "PATH": os.environ.get("PATH", ""),
                                     "HOME": str(Path.home())}, clear=True), \
             patch.object(socket.socket, "connect", side_effect=AssertionError("network forbidden")), \
             patch("deepagents.graph.resolve_model", return_value=model):
            directory = Path(tmp)
            result = run_deepagents("offline-model", directory, str(FACTS), "Synthetic test", timeout_s=10)
            self.assertEqual(result["ended"], "success")
            events = [json.loads(line) for line in (directory / "audit.jsonl").read_text().splitlines()]
            self.assertEqual([e["outcome"] for e in events], ["rejected", "success"])
            self.assertEqual(events[1]["arguments"]["revises"], "A001")
            self.assertEqual(events[1]["result"]["finding_id"], "A002")
            self.assertTrue(verify_audit(directory / "audit.jsonl")["passed"])
