"""Optional, offline integration with the real API graph and a scripted model.

Run after installing .[agent]. No provider credentials or model calls are used.
"""
import importlib.util
import json
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from agent.run import INVESTIGATOR_TOOLS, run_deepagents


ROOT = Path(__file__).resolve().parent.parent
FACTS = ROOT / "fixtures/sample_facts.json"
HAS_API = importlib.util.find_spec("deepagents") is not None


@unittest.skipUnless(HAS_API, "install .[agent] to exercise the real API graph offline")
class APIIntegration(unittest.TestCase):
    def invoke(self, calls):
        from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
        from langchain_core.messages import AIMessage, ToolMessage
        from pydantic import Field

        class OfflineModel(FakeMessagesListChatModel):
            advertised: list[str] = Field(default_factory=list)
            tool_results: list = Field(default_factory=list)

            def bind_tools(self, tools, **kwargs):
                self.advertised[:] = [tool.name for tool in tools]
                return self

            def _generate(self, messages, *args, **kwargs):
                self.tool_results.extend(m for m in messages if isinstance(m, ToolMessage))
                return super()._generate(messages, *args, **kwargs)

        model = OfflineModel(responses=[
            AIMessage(content="", tool_calls=calls), AIMessage(content="offline done")])
        with tempfile.TemporaryDirectory() as directory, \
             patch.dict(os.environ, {"LANGSMITH_TRACING": "false"}, clear=True), \
             patch.object(socket.socket, "connect", side_effect=AssertionError("network forbidden")), \
             patch("deepagents.graph.resolve_model", return_value=model) as resolver:
            result = run_deepagents("n1-offline", Path(directory), str(FACTS),
                                    "Only this synthetic public prompt", timeout_s=10)
        self.assertEqual(resolver.call_args_list[0].args[0], "anthropic:n1-offline")
        self.assertEqual(result["ended"], "success")
        self.assertEqual(result["summary"], "offline done")
        self.assertEqual(set(model.advertised), set(INVESTIGATOR_TOOLS))
        return {item.tool_call_id: item for item in model.tool_results}

    def test_actual_async_graph_reads_sql_and_fact(self):
        results = self.invoke([
            {"name": "sql", "args": {"query": "SELECT COUNT(*) FROM facts"}, "id": "count"},
            {"name": "fact", "args": {"id": 3100}, "id": "record"},
        ])
        count = len(json.loads(FACTS.read_text())["facts"])
        self.assertEqual(json.loads(results["count"].content)["rows"], [[count]])
        self.assertEqual(json.loads(results["record"].content)["id"], 3100)

    def test_hidden_framework_tools_are_also_refused_at_dispatch(self):
        results = self.invoke([
            {"name": "write_file", "args": {"file_path": "/forbidden", "content": "must not write"}, "id": "write"},
            {"name": "read_file", "args": {"file_path": "/private-key"}, "id": "read"},
            {"name": "task", "args": {"description": "must not delegate", "subagent_type": "general-purpose"}, "id": "delegate"},
        ])
        for result in results.values():
            self.assertEqual(result.status, "error")
            self.assertEqual(result.content, "This tool is not available to the investigator.")
        self.assertEqual(set(results), {"write", "read", "delegate"})

    def test_sql_mutation_is_refused_through_the_real_graph(self):
        result = self.invoke([
            {"name": "sql", "args": {"query": "DELETE FROM facts"}, "id": "mutate"},
        ])["mutate"]
        self.assertIn("not authorized", json.loads(result.content)["error"])


if __name__ == "__main__":
    unittest.main()
