"""Time limits apply even when the investigation emits no output."""
import asyncio
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import Mock, patch

from agent.run import run_claude_code, run_deepagents

REAL_POPEN = subprocess.Popen


class InvestigationDeadline(unittest.TestCase):
    def local_cli(self, program, limit):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env = {"COP_FACTS": "unused", "COP_RUN_DIR": str(root), "COP_PROPOSER": "test"}

            def fake_cli(_command, **kwargs):
                return REAL_POPEN([sys.executable, "-c", program], **kwargs)

            with patch("agent.run.subprocess.Popen", side_effect=fake_cli), contextlib.redirect_stdout(io.StringIO()):
                return run_claude_code("test", root, env, limit, "PUBLIC PROMPT")

    def test_silent_cli_is_stopped_by_deadline(self):
        started = time.monotonic()
        result = self.local_cli("import time; time.sleep(10)", 0.15)
        self.assertEqual(result["ended"], "time_limit")
        self.assertNotEqual(result["exit_code"], 0)
        self.assertLess(time.monotonic() - started, 3)

    def test_successful_cli_keeps_result(self):
        event = {"type": "result", "result": "done", "subtype": "success", "num_turns": 1}
        result = self.local_cli("print(" + repr(json.dumps(event)) + ")", 5)
        self.assertEqual((result["summary"], result["ended"], result["exit_code"]), ("done", "success", 0))

    def test_failed_cli_is_not_reported_as_success(self):
        result = self.local_cli("raise SystemExit(3)", 5)
        self.assertEqual((result["ended"], result["exit_code"]), ("process_error", 3))

    def test_api_investigation_is_cancelled_at_deadline(self):
        cancelled = []

        async def silent(*args, **kwargs):
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                cancelled.append(True)
                raise

        backend = Mock();backend.ainvoke = silent
        deep = types.ModuleType("deepagents");deep.create_deep_agent = Mock(return_value=backend)
        tools = types.ModuleType("langchain_core.tools");tools.tool = lambda function: function
        with tempfile.TemporaryDirectory() as directory, \
             patch.dict("sys.modules", {"deepagents": deep, "langchain_core.tools": tools}), \
             patch("agent.tools.Workbench"):
            result = run_deepagents("test", Path(directory), "unused", "PUBLIC PROMPT", timeout_s=0.01)
        self.assertEqual(result["ended"], "time_limit")
        self.assertEqual(cancelled, [True])


if __name__ == "__main__":
    unittest.main()
