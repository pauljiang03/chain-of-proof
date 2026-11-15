"""The ablation's fixed four-tool dispatch, shared by single and stdio sessions.

The module name is retained for the runtime lane; no MCP server or model process is
launched. The investigator uses ``comparison.ablation.runtime session`` locally.
"""
from __future__ import annotations


TOOLS = ("forms", "sql", "fact", "check")


def make_workbench(arm, facts, run_dir):
    if arm == "A":
        from comparison.ablation.capture import ReceiptWorkbench
        return ReceiptWorkbench(facts, run_dir, proposer="ablation-subagent")
    if arm == "C":
        from agent.tools import Workbench
        return Workbench(facts, run_dir, proposer="ablation-subagent")
    raise ValueError("arm must be A or C")


def dispatch(bench, tool: str, arguments: dict):
    if tool not in TOOLS:
        raise ValueError("only forms, sql, fact and check are available")
    if not isinstance(arguments, dict):
        raise ValueError("arguments must be an object")
    allowed = {"forms": set(), "sql": {"query"}, "fact": {"id"},
               "check": {"question", "claim", "claims", "revises"}}[tool]
    if set(arguments) - allowed:
        raise ValueError("unsupported tool argument")
    if tool == "forms":
        return bench.forms()
    if tool == "sql":
        if not isinstance(arguments.get("query"), str):
            raise ValueError("sql requires a query string")
        return bench.sql(arguments["query"])
    if tool == "fact":
        if type(arguments.get("id")) is not int:
            raise ValueError("fact requires an integer id")
        return bench.fact(arguments["id"])
    if not isinstance(arguments.get("question"), str):
        raise ValueError("check requires a question string")
    if ("claim" in arguments) == ("claims" in arguments):
        raise ValueError("check requires either claim or claims")
    if "revises" in arguments and not isinstance(arguments["revises"], str):
        raise ValueError("revises must be a string")
    kwargs = {"revises": arguments["revises"]} if "revises" in arguments else {}
    if "claim" in arguments:
        if not isinstance(arguments["claim"], dict):
            raise ValueError("claim must be a JSON object")
        return bench.check(arguments["question"], arguments["claim"], **kwargs)
    if (not isinstance(arguments["claims"], list) or not arguments["claims"]
            or not all(isinstance(claim, dict) for claim in arguments["claims"])):
        raise ValueError("claims must be a nonempty array of objects")
    return [bench.check(arguments["question"], claim, **kwargs)
            for claim in arguments["claims"]]
