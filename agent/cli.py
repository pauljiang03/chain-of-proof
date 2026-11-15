"""Command-line access to the investigator's tools.

    python3 -m agent.cli forms
    python3 -m agent.cli sql "SELECT id, kind, time_utc, obj, aux FROM facts WHERE kind='usbInsert'"
    python3 -m agent.cli fact 12
    python3 -m agent.cli check --question "..." --claim '{"usbConnected": [1]}' [--claim ...]

COP_FACTS names the evidence file, COP_RUN_DIR the directory proposals are logged in.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from agent.tools import Workbench


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m agent.cli")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("forms", help="the statement forms you may propose")
    p = sub.add_parser("sql", help="one read-only SELECT over the facts table")
    p.add_argument("query")
    p = sub.add_parser("fact", help="one record in full, with where it came from")
    p.add_argument("id", type=int)
    p = sub.add_parser("check", help="propose a claim; the kernel accepts or refuses it")
    p.add_argument("--question", required=True)
    p.add_argument("--claim", required=True, action="append",
                   help="repeat --claim to propose several claims for one question")
    for command in ("plan", "review"):
        sub.add_parser(command)
    p = sub.add_parser("evidence-needs")
    p.add_argument("--proof-gap", help="diagnostic JSON returned by check")
    p = sub.add_parser("collect")
    p.add_argument("--reader", required=True)
    p.add_argument("--exhibit", required=True)
    p = sub.add_parser("update-question")
    p.add_argument("--id", required=True)
    p.add_argument("--finding", action="append")
    p.add_argument("--searched", action="append")
    p.add_argument("--unresolved", action="append")
    p.add_argument("--next-action", action="append")
    p.add_argument("--status", choices=("not_started", "in_progress", "blocked", "reviewed"))
    args = ap.parse_args(argv)
    bench = Workbench(os.environ.get("COP_FACTS", "evidence/case_facts.json"),
                      os.environ.get("COP_RUN_DIR", "runs/dev"),
                      os.environ.get("COP_PROPOSER", "agent"))
    if args.cmd in ("plan", "review"):
        out = getattr(bench, args.cmd)()
    elif args.cmd == "evidence-needs":
        out = bench.evidence_needs(json.loads(args.proof_gap) if args.proof_gap else None)
    elif args.cmd == "collect":
        out = bench.collect(args.reader, args.exhibit)
    elif args.cmd == "update-question":
        out = bench.update_question(args.id, finding_ids=args.finding, searched=args.searched,
            unresolved=args.unresolved, next_actions=args.next_action, status=args.status)
    elif args.cmd == "forms":
        out = bench.forms()
    elif args.cmd == "sql":
        out = bench.sql(args.query)
    elif args.cmd == "fact":
        out = bench.fact(args.id)
    else:
        out = [bench.check(args.question, c) for c in args.claim]
        out = out[0] if len(out) == 1 else out
    if args.cmd == "sql" and "rows" in out:      # one row per line: compact to read
        print(json.dumps(out["columns"], ensure_ascii=False))
        for row in out["rows"]:
            print(json.dumps(row, ensure_ascii=False))
        if "truncated" in out:
            print(out["truncated"])
    else:
        print(json.dumps(out, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
