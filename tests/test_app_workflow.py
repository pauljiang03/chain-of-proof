"""HTTP -> child worker -> proof pipeline, without a model provider."""
from __future__ import annotations

import http.client
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.jobs import JobManager
from app.server import create_server


class OfflineManager(JobManager):
    """Replace only the child launch with a deterministic test-only backend."""

    pause = False

    def config(self):
        value = super().config()
        for backend in value["backends"]:
            backend["available"] = True
        return value

    def _spawn(self, command, env):
        test_env = dict(env, COP_APP_TEST_PAUSE="1" if self.pause else "0")
        return subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--worker",
                                 command[command.index("--root") + 1],
                                 command[command.index("--spec") + 1]],
                                cwd=ROOT, env=test_env, stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                start_new_session=(os.name == "posix"))


def _offline_worker(root, spec):
    from agent import run
    from agent.tools import Workbench
    from app.jobs import _worker

    def investigate(model, run_dir, facts, prompt, timeout_s):
        bench = Workbench(facts, run_dir, "offline app integration test")
        bench.fact(3100)
        refused = bench.check("Which search?", {"usbConnected": [3100]})
        accepted = bench.check("Which search?", {"searched": [3100]},
                               revises=refused["finding_id"])
        if accepted["status"] != "verified":
            raise AssertionError("synthetic proof was not accepted")
        if os.environ.get("COP_APP_TEST_PAUSE") == "1":
            time.sleep(60)
        return {"summary": "Synthetic investigator completed without a provider.",
                "turns": 1, "tool_calls": 3, "seconds": 0, "ended": "success"}

    run.run_deepagents = investigate
    return _worker(root, spec)


class AppWorkflow(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.manager = OfflineManager(self.root)
        self.server = create_server(self.root, 0, manager=self.manager)
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()
        self.addCleanup(self._close)
        self.token = self.request("GET", "/api/config")[1]["token"]

    def _close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def request(self, method, path, payload=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=20)
        try:
            headers = {}
            body = None
            if payload is not None:
                body = json.dumps(payload)
                headers = {"Content-Type": "application/json", "X-COP-Token": self.token,
                           "Origin": f"http://127.0.0.1:{self.server.server_port}"}
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            raw = response.read()
            data = json.loads(raw) if response.getheader("Content-Type", "").startswith("application/json") else raw
            return response.status, data
        finally:
            connection.close()

    def start(self, name, **changes):
        payload = {
            "name": name, "facts": str(ROOT / "fixtures/sample_facts.json"),
            "backend": "deepagents", "model": "offline-test", "minutes": 1,
            "title": "Synthetic local app test", "brief": "Review only the supplied synthetic rows.",
            "questions": ["Which search is recorded?"]}
        payload.update(changes)
        status, result = self.request("POST", "/api/investigations", payload)
        self.assertEqual(status, 200, result)
        self.assertEqual(result, {"name": name, "status": "running"})

    def wait_for(self, name, predicate):
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            status, snapshot = self.request("GET", "/api/run?name=" + name)
            self.assertEqual(status, 200, snapshot)
            if predicate(snapshot):
                return snapshot
            time.sleep(0.03)
        self.fail("Synthetic job did not reach the expected state")

    def assert_report(self, name, snapshot):
        self.assertEqual(snapshot["run"]["stats"]["verified"], 1)
        self.assertEqual(snapshot["run"]["stats"]["rejected"], 1)
        self.assertTrue(snapshot["run"]["audit"]["passed"])
        self.assertFalse(snapshot["run"]["case"]["scoring_requested"])
        expected = ["fact", "check", "check"] + (["review"] if snapshot["status"] == "completed" else [])
        self.assertEqual([entry["tool"] for entry in snapshot["events"]], expected)
        self.assertEqual(snapshot["events"][2]["arguments"]["revises"], "A001")
        sentence = snapshot["run"]["findings"][0]["english"]
        for fmt in ("html", "md", "json"):
            status, report = self.request("GET", f"/api/report?name={name}&format={fmt}&download=1")
            self.assertEqual(status, 200, report)
            if fmt == "json":
                self.assertEqual(report["findings"], snapshot["run"]["findings"])
            else:
                self.assertTrue(report)
        self.assertTrue(sentence)
        self.assertTrue((self.root / "runs" / name / "report.md").is_file())
        self.assertTrue((self.root / "runs" / name / "case-profile.json").is_file())

    def test_actual_pipeline_produces_downloadable_report_without_model_calls(self):
        # The browser intentionally sends blank optional fields for defaults.
        self.start("complete", model="", brief="", questions=[])
        snapshot = self.wait_for("complete", lambda s: s["status"] != "running")
        self.assertEqual(snapshot["status"], "completed", snapshot["error"])
        self.assertEqual(snapshot["run"]["case"]["model"], "claude-opus-5-5")
        profile = json.loads((self.root / "runs/complete/case-profile.json").read_text())
        self.assertTrue(profile["brief"])
        self.assertTrue(profile["questions"])
        self.assert_report("complete", snapshot)
        status, runs = self.request("GET", "/api/runs")
        self.assertEqual(status, 200)
        self.assertEqual(next(r for r in runs["runs"] if r["name"] == "complete")["status"], "completed")
        status, _ = self.request("POST", "/api/investigations", {
            "name": "complete", "facts": str(ROOT / "fixtures/sample_facts.json")})
        self.assertEqual(status, 409)

    def test_stop_preserves_real_certificates_and_partial_report(self):
        self.manager.pause = True
        self.start("cancelled")
        self.wait_for("cancelled", lambda s: len(s["events"]) == 3)
        status, result = self.request("POST", "/api/stop", {"name": "cancelled"})
        self.assertEqual(status, 200, result)
        self.assertEqual(result["status"], "cancelled")
        snapshot = self.wait_for("cancelled", lambda s: s["status"] != "running")
        self.assertEqual(snapshot["status"], "cancelled")
        self.assertEqual(snapshot["run"]["case"]["ended"], "cancelled")
        self.assert_report("cancelled", snapshot)

    def test_cli_investigate_saves_html_markdown_and_json_from_actual_pipeline(self):
        from app import cli

        output = io.StringIO()
        with patch("app.cli._job_manager", return_value=self.manager), \
             patch("app.cli.POLL_SECONDS", 0.01), contextlib.redirect_stdout(output):
            code = cli.main(["investigate", "--name", "terminal", "--facts",
                             str(ROOT / "fixtures/sample_facts.json"),
                             "--backend", "deepagents", "--minutes", "1",
                             "--title", "Synthetic terminal workflow", "--question",
                             "Which search is recorded?"], root=self.root)
        self.assertEqual(code, 0, output.getvalue())
        directory = self.root / "runs/terminal"
        data = json.loads((directory / "run.json").read_text())
        self.assertEqual(data["stats"]["verified"], 1)
        self.assertTrue(data["audit"]["passed"])
        self.assertTrue((directory / "report.md").is_file())
        self.assertIn("<!doctype html>", (directory / "report.html").read_text().lower())
        self.assertIn(str(directory / "report.html"), output.getvalue())


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--worker":
        raise SystemExit(_offline_worker(sys.argv[2], sys.argv[3]))
    unittest.main()
