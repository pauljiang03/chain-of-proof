"""The investigator's four tools as a Model Context Protocol server over stdio.

Hand-written JSON-RPC, standard library only. This is how the tools reach a headless
Claude Code session: that session gets these four tools and no others (no shell, no
file access), so it cannot read the answer key or anything else on the machine.

COP_FACTS names the evidence file, COP_RUN_DIR the directory proposals are logged in.
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

def tools_for(names) -> list:
    """The tools a session is given. COP_TOOLS picks them; the default is the four."""
    by_name = {t["name"]: t for t in TOOLS + [CONCLUDE_TOOL]}
    return [by_name[n] for n in names]


def call(bench: Workbench, name: str, args: dict) -> str:
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
