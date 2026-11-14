"""Restrict the optional API harness to the investigator's evidence tools.

Imported only by the API backend; core commands do not require LangChain.
The same allowlist applies to tool advertising and actual dispatch.
"""
from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage


class EvidenceToolsOnly(AgentMiddleware):
    def __init__(self, names):
        self.names = frozenset(names)

    def _request(self, request):
        return request.override(tools=[tool for tool in request.tools
            if (tool.get("name") if isinstance(tool, dict) else tool.name) in self.names])

    def _denied(self, request):
        if request.tool_call["name"] not in self.names:
            return ToolMessage(content="This tool is not available to the investigator.",
                               tool_call_id=request.tool_call["id"], status="error")
        return None

    def wrap_model_call(self, request, handler):
        return handler(self._request(request))

    async def awrap_model_call(self, request, handler):
        return await handler(self._request(request))

    def wrap_tool_call(self, request, handler):
        denied = self._denied(request)
        return denied if denied is not None else handler(request)

    async def awrap_tool_call(self, request, handler):
        denied = self._denied(request)
        return denied if denied is not None else await handler(request)
