"""The audit, diagnostics, revision, citation and bundle paths work together."""
import json
from pathlib import Path
import tempfile
import unittest

from agent import mcp_server
from agent.audit import verify_audit
from agent.tools import Workbench
from checker import export, report
from verifier.verify import verify_run


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

    def test_ordinary_duplicate_and_explicit_new_revision_remain_distinct(self):
        with tempfile.TemporaryDirectory() as tmp:
            bench = Workbench(FACTS, tmp)
            original = bench.check("Q1", {"searched": [3100]})
            wrong = bench.check("Q1", {"usbConnected": [3100]})
            revised = bench.check("Q1", {"searched": [3100]}, revises=wrong["finding_id"])
            self.assertEqual(revised["status"], "verified")
            self.assertNotEqual(revised["finding_id"], original["finding_id"])
            self.assertNotIn("already proposed", revised.get("note", ""))
