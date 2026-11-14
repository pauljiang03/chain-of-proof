"""API deadlines stop queued work and claim batches in the real offline graph."""
import importlib.util
import os
from pathlib import Path
import socket
import tempfile
import threading
import time
import types
import unittest
from unittest.mock import Mock, patch

from agent.run import run_deepagents


HAS_API = importlib.util.find_spec("deepagents") is not None


@unittest.skipUnless(HAS_API, "install .[agent] to exercise the real API graph offline")
class APIDeadline(unittest.TestCase):
    def setUp(self):
        self.started = []
        self.finished = []
        self.lock = threading.Lock()
        self.bench = Mock()

    def work(self, label, delay):
        def perform(*args):
            with self.lock:
                self.started.append((label, args))
            time.sleep(delay)
            with self.lock:
                self.finished.append(label)
            return {"status": "rejected", "reason": "synthetic evidence tool"}
        return perform

    def invoke_graph(self, calls, timeout_s):
        from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
        from langchain_core.messages import AIMessage

        class OfflineModel(FakeMessagesListChatModel):
            def bind_tools(self, tools, **kwargs):
                return self

        model = OfflineModel(responses=[AIMessage(content="", tool_calls=calls), AIMessage(content="done")])
        with tempfile.TemporaryDirectory() as directory, \
             patch.dict(os.environ, {"LANGSMITH_TRACING": "false"}, clear=True), \
             patch.object(socket.socket, "connect", side_effect=AssertionError("network forbidden")), \
             patch("deepagents.graph.resolve_model", return_value=model), \
             patch("agent.tools.Workbench", return_value=self.bench):
            return run_deepagents("deadline-offline", Path(directory), "unused", "PUBLIC ONLY",
                                  timeout_s=timeout_s)

    def test_real_graph_stops_batch_after_one_active_check_finishes(self):
        self.bench.check.side_effect = self.work("check", 0.25)
        result = self.invoke_graph([{"name": "check", "id": "batch", "args": {
            "question": "Synthetic claims", "claims": [{"claim": n} for n in range(8)]}}], 0.15)
        self.assertEqual(result["ended"], "time_limit")
        self.assertEqual(len(self.started), 1)
        self.assertEqual(self.finished, ["check"])
        self.assertEqual(self.started[0][1][1], {"claim": 0})

    def test_real_graph_refuses_queued_tools_after_deadline(self):
        calls = [
            {"name": "check", "id": "check", "args": {"question": "q", "claims": [{}]}},
            {"name": "sql", "id": "sql", "args": {"query": "SELECT 1"}},
            {"name": "fact", "id": "fact", "args": {"id": 1}},
            {"name": "forms", "id": "forms", "args": {}},
            {"name": "conclude", "id": "conclude", "args": {"text": "q", "finding_ids": []}},
        ]
        for call in calls:
            getattr(self.bench, call["name"]).side_effect = self.work(call["name"], 0.25)
        result = self.invoke_graph(calls, 0.15)
        self.assertEqual(result["ended"], "time_limit")
        self.assertEqual(len(self.started), 1)
        self.assertEqual(self.finished, [self.started[0][0]])

    def test_real_graph_completes_batch_within_budget(self):
        self.bench.check.side_effect = self.work("check", 0)
        claims = [{"claim": n} for n in range(3)]
        result = self.invoke_graph([{"name": "check", "id": "batch", "args": {
            "question": "Synthetic claims", "claims": claims}}], 5)
        self.assertEqual(result["ended"], "success")
        self.assertEqual([entry[1][1] for entry in self.started], claims)
        self.assertEqual(len(self.finished), len(claims))

    def test_guard_expiry_reports_budget_even_before_async_timer_can_run(self):
        self.bench.check.side_effect = self.work("check", 0.08)

        def blocking_graph(*, model, tools):
            check = next(tool for tool in tools if tool.name == "check")

            async def invoke(*args, **kwargs):
                # Deliberately block the event loop so only the tool's monotonic
                # guard, not wait_for's callback, can catch this batch deadline.
                check.invoke({"question": "q", "claims": [{}, {}, {}]})
                raise AssertionError("batch should have stopped")

            return types.SimpleNamespace(ainvoke=invoke)

        with tempfile.TemporaryDirectory() as directory, \
             patch("agent.tools.Workbench", return_value=self.bench), \
             patch("agent.run._create_api_agent", side_effect=blocking_graph):
            result = run_deepagents("deadline-offline", Path(directory), "unused", "PUBLIC ONLY", timeout_s=0.04)
        self.assertEqual(result["ended"], "time_limit")
        self.assertEqual(len(self.started), 1)


if __name__ == "__main__":
    unittest.main()
