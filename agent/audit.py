"""With and without the checker: the same model, the same records, the same questions.

    python3 -m agent.audit --name report-audit
    python3 -m agent.audit --name report-audit --resume     # finish an interrupted audit

1. The model writes a normal findings report. It can look at the records but has no
   checker (tools: sql, fact).
2. An auditor puts every sentence of that report through the checker and files a
   verdict on each (tools: forms, sql, fact, check, record).
   The auditor works through the report a few sentences per session and records each
   verdict as it goes, so an interrupted run loses at most one sentence.
3. The verdicts are checked against the certificates: "certified" and "weaker" count
   only if they cite findings the kernel really certified in this run.

Writes runs/<name>/: plain_report.md, the proposal log and certificates, and audit.json
(one entry per report sentence: verdict, reason, and the certified sentences beside it).

The verdict on whether a certified sentence says the same as a report sentence is the
auditor model's judgment. It is shown side by side so a person can check it.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

from agent.brief import REPORT_BRIEF, audit_brief
from agent.mcp_server import VERDICTS
from agent.run import ROOT, run_claude_code

STATEMENT = re.compile(r"^\s*\**F(\d+)\**\s*[:.]\s*\**\s*(.+?)\s*$")


def parse_statements(report: str):
    out, seen = [], set()
    for line in report.splitlines():
        m = STATEMENT.match(line)
        if m and int(m.group(1)) not in seen:
            seen.add(int(m.group(1)))
            out.append((int(m.group(1)), m.group(2)))
    return out


def merge(run_dir: Path, statements) -> dict:
    """Join report sentences, auditor verdicts and the certificates they cite."""
    certs = {p.stem: json.loads(p.read_text()) for p in run_dir.glob("A*.json")}
    verdicts = {}
    log = run_dir / "audit.jsonl"
    for line in (log.read_text().splitlines() if log.is_file() else []):
        row = json.loads(line)
        verdicts[row["statement"]] = row            # a later verdict replaces an earlier one
    rows = []
    for n, text in statements:
        v = verdicts.get(n, {"verdict": "not_audited", "finding_ids": [], "reason": ""})
        cited = [certs[i] for i in v["finding_ids"] if i in certs]
        verdict = v["verdict"]
        if verdict in ("certified", "weaker") and not cited:
            verdict = "refused"                      # no certificate behind the verdict
            v = dict(v, reason="auditor cited no certified finding. " + v["reason"])
        rows.append({"statement": n, "text": text, "verdict": verdict, "reason": v["reason"],
                     "findings": [{"finding_id": c["finding_id"], "strength": c["strength"],
                                   "english": c["english"]} for c in cited]})
    counts = Counter(r["verdict"] for r in rows)
    return {"statements": rows,
            "counts": {k: counts.get(k, 0) for k in VERDICTS + ("not_audited",)}}


def recorded(run_dir: Path) -> set:
    """Statement numbers that already have a verdict on file."""
    log = run_dir / "audit.jsonl"
    return {json.loads(line)["statement"]
            for line in (log.read_text().splitlines() if log.is_file() else [])}


def chunks(numbers, size: int):
    return [numbers[i:i + size] for i in range(0, len(numbers), size)]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Plain report vs checker, sentence by sentence.")
    ap.add_argument("--name", default="audit")
    ap.add_argument("--model", default="opus")
    ap.add_argument("--facts", default="evidence/case_facts.json")
    ap.add_argument("--minutes", type=int, default=15, help="time limit for each session")
    ap.add_argument("--chunk", type=int, default=10, help="statements per auditor session")
    ap.add_argument("--report", help="audit this existing report instead of writing a new one")
    ap.add_argument("--resume", action="store_true",
                    help="keep runs/<name> and audit only the statements with no verdict yet")
    args = ap.parse_args(argv)

    run_dir = ROOT / "runs" / args.name
    env = dict(COP_FACTS=str((ROOT / args.facts).resolve()), COP_RUN_DIR=str(run_dir),
               COP_PROPOSER=f"auditor:claude-code:{args.model}")
    if args.resume:
        if not (run_dir / "plain_report.md").is_file():
            print(f"nothing to resume: {run_dir.relative_to(ROOT)}/plain_report.md is missing")
            return 1
        report = (run_dir / "plain_report.md").read_text()
    else:
        if args.report:
            report = Path(args.report).read_text()
        if run_dir.exists():
            shutil.rmtree(run_dir)
        run_dir.mkdir(parents=True)
        if not args.report:
            print("1. writing the plain report (no checker)")
            meta = run_claude_code(args.model, run_dir, env, args.minutes * 60,
                                   prompt=REPORT_BRIEF, tools=("sql", "fact"),
                                   transcript="transcript_report.jsonl")
            report = meta["summary"]
            print(f"   {meta['tool_calls']} tool calls, {meta['seconds']} s, ended: {meta['ended']}")
        (run_dir / "plain_report.md").write_text(report.rstrip("\n") + "\n")
    statements = parse_statements(report)
    print(f"   {len(statements)} statements")
    if not statements:
        print("no numbered statements found in the report")
        return 1

    print("2. putting each statement through the checker")
    for attempt in (1, 2):                 # the second pass picks up what a session dropped
        todo = [n for n, _ in statements if n not in recorded(run_dir)]
        for k, part in enumerate(chunks(todo, args.chunk), 1):
            print(f"   F{part[0]} to F{part[-1]}", flush=True)
            meta = run_claude_code(args.model, run_dir, env, args.minutes * 60,
                                   prompt=audit_brief(statements, only=part),
                                   tools=("forms", "sql", "fact", "check", "record"),
                                   transcript=f"transcript_audit_{attempt}_{k:02d}.jsonl")
            print(f"   {meta['tool_calls']} tool calls, {meta['seconds']} s, "
                  f"ended: {meta['ended']}", flush=True)

    result = merge(run_dir, statements)
    result["model"] = args.model
    (run_dir / "audit.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print("\n3. verdicts")
    for k, n in result["counts"].items():
        if n:
            print(f"   {k:<15}{n:>4}")
    for r in result["statements"]:
        if r["verdict"] not in ("certified",):
            print(f"\n   F{r['statement']} [{r['verdict']}] {r['text'][:200]}\n      why: {r['reason'][:300]}")
    left = result["counts"]["not_audited"]
    if left:
        print(f"\n{left} statements have no verdict yet: run again with --resume")
    return 1 if left else 0


if __name__ == "__main__":
    sys.exit(main())
