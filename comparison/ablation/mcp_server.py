"""Versioned ablation tool dispatch, shared by single and stdio sessions.

The module name is retained for the runtime lane; no MCP server or model process is
launched. The investigator uses ``comparison.ablation.runtime session`` locally.
"""
from __future__ import annotations

from agent.audit import audited


TOOLS = ("forms", "sql", "fact", "check")
PROTOCOLS = ("literal-v1", "claim-bindings-v2", "claim-bindings-v3")
BINDING_TOOLS = TOOLS + ("plan", "update_question", "inventory_page")


def tools_for(protocol="literal-v1"):
    if protocol not in PROTOCOLS:
        raise ValueError("unknown ablation protocol")
    if protocol == "claim-bindings-v3":
        return BINDING_TOOLS + ("checkpoint", "preview")
    return TOOLS if protocol == "literal-v1" else BINDING_TOOLS


def _neutral_plan(bench):
    """Public work notes only; never consult the product answer store/certificates."""
    from agent.investigation import Investigation
    from agent.inventory_pages import inventory_progress
    from agent.coverage_plan import coverage_pass
    state = Investigation(bench.run_dir).snapshot()
    neutral = {key: state[key] for key in ("schema_version", "case_id", "name", "time_zone", "facts_sha256") if key in state}
    neutral["questions"] = [{key: question[key] for key in
        ("id", "prompt", "answer_schema", "work_status", "searched", "unresolved", "next_actions") if key in question}
        for question in state.get("questions", [])]
    try:
        inventory = inventory_progress(bench.run_dir, evidence_sha256=state.get("facts_sha256"))
    except (ValueError, OSError, TypeError) as error:
        inventory = {"status": "invalid", "error_type": type(error).__name__, "traversals": []}
    neutral["coverage"] = coverage_pass(neutral, answers=None, inventory_progress=inventory)
    session = getattr(bench, "_ablation_session", None)
    if session is not None and session.get("protocol") == "claim-bindings-v3":
        from comparison.ablation.checkpoints import completion_status
        neutral["completion"] = completion_status(bench.run_dir, session, bench.source)
    neutral["disclaimer"] = "Public work notes and returned-row progress only; no certificate, relevance, accuracy or completeness is inferred."
    return neutral


class _NeutralWorkflow:
    @audited
    def forms(self):
        from agent.answer_projection import tool_catalog
        from agent.tools import Workbench
        # One audit event binds the complete returned static catalog in both arms.
        return dict(Workbench.forms.__wrapped__(self), answer_projection=tool_catalog())

    @audited
    def plan(self):
        return _neutral_plan(self)

    @audited
    def update_question(self, question_id, searched=None, unresolved=None, next_actions=None, status=None):
        from agent.investigation import Investigation
        Investigation(self.run_dir).update(question_id, searched=searched, unresolved=unresolved,
                                            next_actions=next_actions, status=status)
        return _neutral_plan(self)


def make_workbench(arm, facts, run_dir, protocol="literal-v1"):
    tools_for(protocol)
    if arm == "A":
        from comparison.ablation.capture import ReceiptWorkbench
        kind = ReceiptWorkbench if protocol == "literal-v1" else type("NeutralReceiptWorkbench", (_NeutralWorkflow, ReceiptWorkbench), {})
        return kind(facts, run_dir, proposer="ablation-subagent")
    if arm == "C":
        from agent.tools import Workbench
        kind = Workbench if protocol == "literal-v1" else type("NeutralCheckedWorkbench", (_NeutralWorkflow, Workbench), {})
        return kind(facts, run_dir, proposer="ablation-subagent")
    raise ValueError("arm must be A or C")


def dispatch(bench, tool: str, arguments: dict, protocol="literal-v1"):
    if tool not in tools_for(protocol):
        raise ValueError("tool is unavailable in this ablation protocol")
    if not isinstance(arguments, dict):
        raise ValueError("arguments must be an object")
    allowed = {"forms": set(), "sql": {"query"}, "fact": {"id"},
               "check": {"question", "claim", "claims", "revises"},
               "plan": set(), "update_question": {"question_id", "searched", "unresolved", "next_actions", "status"},
               "inventory_page": {"question_id", "kinds", "exhibits", "page_size", "cursor"}}[tool]
    if set(arguments) - allowed:
        raise ValueError("unsupported tool argument")
    if tool == "plan":
        return bench.plan()
    if tool in ("update_question", "inventory_page"):
        if not isinstance(arguments.get("question_id"), str):
            raise ValueError(tool + " requires a public question_id")
        return getattr(bench, tool)(**arguments)
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
