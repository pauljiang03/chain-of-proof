"""Task recovery must not transfer proof authority across evidence versions."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent import continuation, run
from agent.investigation import Investigation
from agent.tools import Workbench
from verifier.verify import verify_run
from checker.facts import open_source

ROOT = Path(__file__).resolve().parent.parent
FACTS = ROOT / "fixtures/sample_facts.json"


class ContinuationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.profile = self.root / "public.json"
        self.profile.write_text(json.dumps({"name": "Synthetic", "brief": "Inspect these records.",
                                           "questions": ["Which search?"], "case_id": "synthetic"}))

    def invoke(self, name, backend, extra=()):
        with patch.object(run, "ROOT", self.root), patch.object(run, "run_deepagents", side_effect=backend), \
             contextlib.redirect_stdout(io.StringIO()):
            return run.main(["--name", name, "--facts", str(FACTS), "--backend", "deepagents",
                             "--case-profile", str(self.profile), "--no-score", *extra])

    @staticmethod
    def first(model, directory, facts, **kwargs):
        bench = Workbench(facts, directory)
        found = bench.check("Which search?", {"searched": [3100]})
        assert found["status"] == "verified"
        bench.update_question("Q1", finding_ids=[found["finding_id"]], searched=["Browser history"],
                              unresolved=["Other browsers"], next_actions=["Inspect more browser records"],
                              status="in_progress")
        return {"summary": "Partial", "turns": 1, "tool_calls": 2, "seconds": 0, "ended": "time_limit"}

    def test_same_evidence_rechecks_claims_and_preserves_original(self):
        self.assertEqual(self.invoke("first", self.first), 0)
        original = self.root / "runs/first"
        before = {p.name: p.read_bytes() for p in original.iterdir() if p.is_file()}
        seen = {}
        def second(model, directory, facts, **kwargs):
            seen.update(Investigation(directory).snapshot())
            return {"summary": "Continued", "turns": 1, "tool_calls": 0, "seconds": 0, "ended": "success"}
        self.assertEqual(self.invoke("second", second, ["--resume-from", str(original)]), 0)
        second_dir = self.root / "runs/second"
        saved = json.loads((second_dir / "run.json").read_text())
        self.assertEqual(saved["stats"]["verified"], 1)
        self.assertTrue(verify_run(saved, open_source(FACTS))["passed"])
        self.assertTrue(json.loads((second_dir / "continuation.json").read_text())["same_evidence"])
        self.assertEqual(seen["questions"][0]["finding_ids"], ["A001"])
        self.assertEqual(before, {p.name: p.read_bytes() for p in original.iterdir() if p.is_file()})
        self.assertIn("continuation", saved["run_manifest"]["inputs"])

    def test_changed_snapshot_clears_old_ids_and_keeps_notes_unverified(self):
        self.invoke("first", self.first)
        changed = self.root / "new.json"
        changed.write_bytes(FACTS.read_bytes() + b"\n")
        previous = continuation.parent(self.root / "runs/first")
        dest = self.root / "runs/changed"
        dest.mkdir()
        receipt = continuation.restore(previous, dest, changed, previous["profile"])
        self.assertFalse(receipt["same_evidence"])
        self.assertEqual(receipt["replayed"], [])
        state = Investigation(dest).snapshot()
        self.assertEqual(state["questions"][0]["finding_ids"], [])
        self.assertFalse((dest / "A001.json").exists())
        self.assertIn("Browser history", json.dumps(state))

    def test_evidence_default_rejects_a_changed_file(self):
        self.invoke("first", self.first)
        previous = continuation.parent(self.root / "runs/first")
        changed = self.root / "changed.json"
        changed.write_bytes(FACTS.read_bytes() + b"\n")
        previous["facts"]["path"] = str(changed)
        with self.assertRaisesRegex(ValueError, "changed"):
            continuation.default_facts(previous)

    def test_active_and_symlink_parents_are_refused(self):
        self.invoke("first", self.first)
        directory = self.root / "runs/first"
        (directory / "app-job.json").write_text('{"status":"running"}')
        # A stale job label after process exit must not prevent recovery.
        self.assertEqual(continuation.parent(directory)["directory"], directory)
        with continuation.active_run(directory):
            with self.assertRaisesRegex(ValueError, "Stop"):
                continuation.parent(directory)
        link = self.root / "link"
        link.symlink_to(directory)
        with self.assertRaisesRegex(ValueError, "symlink"):
            continuation.parent(link)


if __name__ == "__main__":
    unittest.main()
