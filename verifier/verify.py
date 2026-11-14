"""Re-check a certificate without trusting the agent, the stored Lean file, or the report.

    python -m verifier.verify certs/F7.json --facts fixtures/sample_facts.json

Three checks, all rebuilt from the evidence DB:
  1. every cited fact still matches its DB row (row_sha256); for a census ("exactly n
     records of this kind") the cited facts must be every fact of that kind in the DB;
  2. the claim, regenerated as Lean from those rows, is accepted by the kernel;
  3. the English sentence is exactly what the templates produce for that claim.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

from checker import claims
from checker.check import render_lean, run_kernel
from checker.facts import FactSource, open_source


def verify(cert: dict, source: FactSource) -> List[str]:
    """Return the list of problems; empty means the certificate stands."""
    problems: List[str] = []
    try:
        claim = claims.parse(cert["claim"])
    except claims.ClaimError as e:
        return [f"claim does not parse: {e}"]
    try:
        # for a census this is every fact of the kind now in the evidence: if the
        # certificate lists fewer or more, its count is about a different evidence file
        ids, found = claims.cited_facts(claim, source)
    except claims.ClaimError:
        ids, found = claims.fact_ids(claim), source.get(claims.fact_ids(claim))
    cited = {c["id"]: c for c in cert.get("cited_facts", [])}
    if set(cited) != set(ids):
        problems.append(f"cited facts {sorted(cited)} differ from the ids in the claim {sorted(ids)}")
    for i in ids:
        if i not in found:
            problems.append(f"fact {i} is not in the evidence DB")
        elif i in cited and found[i].row_sha256() != cited[i].get("row_sha256"):
            problems.append(f"fact {i} no longer matches its DB row")
    if problems:
        return problems
    kernel = run_kernel(render_lean(cert["finding_id"], [found[i] for i in ids], claim),
                        cert["finding_id"])
    if not kernel["ok"]:
        problems.append("the Lean kernel does not accept the claim for these facts")
    elif kernel["tier"] != cert.get("trust_tier"):
        problems.append(f"trust tier is {kernel['tier']}, certificate says {cert.get('trust_tier')}")
    if claims.strength(claim, found) != cert.get("strength"):
        problems.append("the strength label is not what the claim and its tag facts give")
    if claims.english(claim, found, source) != cert.get("english"):
        problems.append("the English sentence is not what the templates produce for this claim")
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Re-check certificates against the evidence DB.")
    ap.add_argument("certs", nargs="+", help="certificate .json files")
    ap.add_argument("--facts", required=True, help="evidence DB (.duckdb) or fixture (.json)")
    args = ap.parse_args(argv)
    source = open_source(args.facts)
    bad = 0
    for path in args.certs:
        problems = verify(json.loads(Path(path).read_text()), source)
        print(f"{'FAIL' if problems else 'ok  '} {path}")
        for p in problems:
            print(f"       {p}")
        bad += bool(problems)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
