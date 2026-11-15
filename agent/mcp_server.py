"""The investigator's tools as an MCP server over stdio (standard-library JSON-RPC).

A headless Claude Code session gets these tools and nothing else: no shell and no
file access, so it cannot read the answer key. COP_FACTS names the evidence file and
COP_RUN_DIR the directory proposals are logged in.
"""
from __future__ import annotations

import json
import os
import sys

from agent.tools import Workbench

TOOLS = [
    {"name": "forms",
     "description": "List the statement forms you may propose, with their arguments.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "sql",
     "description": "Run one read-only SELECT over the table facts(id, kind, time_utc, t_us, "
                    "uncertainty_us, obj, aux, exhibit, artifact, detail). At most 60 rows.",
     "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}},
                     "required": ["query"]}},
    {"name": "fact",
     "description": "One record in full, with its obj_id / aux_id and where it came from.",
     "inputSchema": {"type": "object", "properties": {"id": {"type": "integer"}},
                     "required": ["id"]}},
    {"name": "check",
     "description": "Propose one or more claims that answer a question. The proof checker "
                    "certifies or refuses each, and says which check failed on a refusal. "
                    "Optionally name a prior proposal with revises to record an explicit correction.",
     "inputSchema": {"type": "object",
                     "properties": {"question": {"type": "string"},
                                    "claims": {"type": "array", "minItems": 1,
                                               "items": {"type": "object"}},
                                    "revises": {"type": "string"}},
                     "required": ["question", "claims"]}},
]

CONCLUDE_TOOL = {
    "name": "conclude",
    "description": "Record one conclusion you draw from certified findings: an inference "
                   "the checker cannot prove (intent, cause, what a pattern means). It is "
                   "shown as your judgment, never as a finding. Every date, time, number "
                   "and name in it must appear in the findings you cite.",
    "inputSchema": {"type": "object",
                    "properties": {"text": {"type": "string"},
                                   "finding_ids": {"type": "array", "minItems": 1,
                                                   "items": {"type": "string"}}},
                    "required": ["text", "finding_ids"]}}

WORKFLOW_TOOLS = [
    {"name": "answer", "description": "Bind supported fields of current certified claims to a public question. Omit bindings for bounded read-only inspection pages. Choose section bindings/leaves/unsupported/conflicts/field_requirements/field_catalog/answers; continue with next_offset and state_token. Paging parameters cannot accompany mutations or previews. preview=true validates proposed bindings without persisting them. Fields need finding_id, part (default 0), field, path (object keys / array indices), and optional format. Values come only from the named claim; relevance and completeness are not proved. Append by default; replace=true replaces this question's bindings.",
     "inputSchema": {"type": "object", "properties": {
         "question_id": {"type": "string"}, "bindings": {"type": "array", "items": {"type": "object"}},
         "replace": {"type": "boolean"}, "preview": {"type": "boolean"},
         "section": {"type": "string", "enum": ["bindings", "leaves", "unsupported", "conflicts", "field_requirements", "field_catalog", "answers"]},
         "offset": {"type": "integer", "minimum": 0},
         "page_size": {"type": "integer", "minimum": 1, "maximum": 100},
         "state_token": {"type": "string", "pattern": "^[0-9a-f]{64}$"}}, "required": ["question_id"], "additionalProperties": False}},
    {"name": "inventory_page", "description": "Read an ID-ordered page of records and save progress for a public question. Continue with the returned cursor and identical filters. Exhaustion applies only to this predicate in this extracted snapshot, not all real-world events.",
     "inputSchema": {"type": "object", "properties": {
         "question_id": {"type": "string"},
         "kinds": {"type": "array", "items": {"type": "string"}},
         "exhibits": {"type": "array", "items": {"type": "string"}},
         "page_size": {"type": "integer", "minimum": 1, "maximum": 250},
         "cursor": {"type": "string"}}, "required": ["question_id"]}},
    {"name": "plan", "description": "Read persistent public questions, searches, supported findings and open work.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "update_question", "description": "Save agent-reported question progress. Refer only to verified finding IDs from this run. This does not prove completeness.",
     "inputSchema": {"type": "object", "properties": {
         "question_id": {"type": "string"},
         **{key: {"type": "array", "items": {"type": "string"}} for key in
            ("finding_ids", "searched", "unresolved", "next_actions")},
         "status": {"type": "string", "enum": ["not_started", "in_progress", "blocked", "reviewed"]}},
         "required": ["question_id"]}},
    {"name": "evidence_needs", "description": "List available readers and evidence needed to resolve a proof gap. Suggestions are diagnostic, not findings.",
     "inputSchema": {"type": "object", "properties": {"proof_gap": {"type": "object"}}}},
    {"name": "collect", "description": "Run an approved reader/exhibit pair returned by evidence_needs. Creates a NEW evidence snapshot for continuation; current facts and certificates stay unchanged.",
     "inputSchema": {"type": "object", "properties": {"reader": {"type": "string"}, "exhibit": {"type": "string"}},
                     "required": ["reader", "exhibit"]}},
    {"name": "review", "description": "Find scoped evidence conflicts and ambiguities. Diagnostics do not establish what actually happened.",
     "inputSchema": {"type": "object", "properties": {}}},
]


def tools_for(names) -> list:
    """The tools a session is given. COP_TOOLS picks them; the default is the four."""
    by_name = {t["name"]: t for t in TOOLS + [CONCLUDE_TOOL] + WORKFLOW_TOOLS}
    return [by_name[n] for n in names]


def call(bench: Workbench, name: str, args: dict) -> str:
    if name in {"answer", "inventory_page"}:
        allowed = ({"question_id", "bindings", "replace", "preview", "section", "offset", "page_size", "state_token"} if name == "answer" else
                   {"question_id", "kinds", "exhibits", "page_size", "cursor"})
        if set(args) - allowed:
            raise ValueError("Unknown " + name + " field")
        return json.dumps(getattr(bench, name)(**args), ensure_ascii=False)
    if name in {"plan", "review"}:
        return json.dumps(getattr(bench, name)(), ensure_ascii=False)
    if name == "update_question":
        allowed = {"question_id", "finding_ids", "searched", "unresolved", "next_actions", "status"}
        if set(args) - allowed:
            raise ValueError("Unknown question update field")
        return json.dumps(bench.update_question(**args), ensure_ascii=False)
    if name == "evidence_needs":
        return json.dumps(bench.evidence_needs(args.get("proof_gap")), ensure_ascii=False)
    if name == "collect":
        return json.dumps(bench.collect(args.get("reader"), args.get("exhibit")), ensure_ascii=False)
    if name == "conclude":
        return json.dumps(bench.conclude(args.get("text", ""), args.get("finding_ids")),
                          ensure_ascii=False)
    if name == "forms":
        return json.dumps(bench.forms(), indent=1, ensure_ascii=False)
    if name == "sql":
        out = bench.sql(str(args.get("query", "")))
        if "rows" not in out:
            return json.dumps(out, ensure_ascii=False)
        lines = [json.dumps(out["columns"], ensure_ascii=False)]
        lines += [json.dumps(r, ensure_ascii=False) for r in out["rows"]]
        return "\n".join(lines + ([out["truncated"]] if "truncated" in out else []))
    if name == "fact":
        return json.dumps(bench.fact(int(args.get("id", -1))), indent=1, ensure_ascii=False)
    if name == "check":
        question = str(args.get("question", ""))
        revision = {"revises": args["revises"]} if "revises" in args else {}
        return json.dumps([bench.check(question, c, **revision) for c in args.get("claims", [])],
                          indent=1, ensure_ascii=False)
    raise KeyError(name)


def main() -> int:
    bench = Workbench(os.environ.get("COP_FACTS", "evidence/case_facts.json"),
                      os.environ.get("COP_RUN_DIR", "runs/dev"),
                      os.environ.get("COP_PROPOSER", "agent"))
    offered = tools_for(os.environ.get("COP_TOOLS", "forms,sql,fact,check").split(","))
    names = {t["name"] for t in offered}
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        msg = json.loads(line)
        method, mid = msg.get("method"), msg.get("id")
        if mid is None:
            continue                                   # a notification: nothing to answer
        reply = {"jsonrpc": "2.0", "id": mid}
        if method == "initialize":
            reply["result"] = {
                "protocolVersion": msg.get("params", {}).get("protocolVersion", "2025-06-18"),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "chain-of-proof", "version": "1.0"}}
        elif method == "ping":
            reply["result"] = {}
        elif method == "tools/list":
            reply["result"] = {"tools": offered}
        elif method == "tools/call":
            params = msg.get("params", {})
            try:
                if params.get("name") not in names:
                    raise KeyError(f"tool {params.get('name')!r} is not offered in this session")
                text, failed = call(bench, params.get("name", ""), params.get("arguments") or {}), False
            except Exception as e:                     # report to the model, keep serving
                text, failed = f"{type(e).__name__}: {e}", True
            reply["result"] = {"content": [{"type": "text", "text": text}], "isError": failed}
        else:
            reply["error"] = {"code": -32601, "message": f"unknown method {method}"}
        sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
