"""Re-check a certificate without trusting the agent, the stored Lean file, or the report.

    python -m verifier.verify certs/F7.json --facts fixtures/sample_facts.json

Three checks, all rebuilt from the evidence DB:
  1. every copied fact field and string still matches its DB row and row_sha256; for a census ("exactly n
     records of this kind") the cited facts must be every fact of that kind in the DB;
  2. the claim, regenerated as Lean from those rows, is accepted by the kernel;
  3. the English sentence, part sentences, rule/strength labels and axioms are exactly
     what regeneration produces for that claim.
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
    saved = cert.get("cited_facts", [])
    cited = {c["id"]: c for c in saved}
    if len(cited) != len(saved):
        problems.append("duplicate cited fact IDs")
    if set(cited) != set(ids):
        problems.append(f"cited facts {sorted(cited)} differ from the ids in the claim {sorted(ids)}")
    for i in ids:
        if i not in found:
            problems.append(f"fact {i} is not in the evidence DB")
        elif i in cited and found[i].row_sha256() != cited[i].get("row_sha256"):
            problems.append(f"fact {i} no longer matches its DB row")
        elif i in cited:
            f = found[i]
            expected = {"id": f.id, "kind": f.kind, "t": f.t, "res": f.res,
                        "obj": f.obj, "obj_text": source.string(f.obj),
                        "aux": f.aux, "aux_text": source.string(f.aux), "prov": f.prov}
            declared = {k: cited[i].get(k) for k in expected}
            # A stored hash alone cannot authenticate the accompanying copied values.
            # JSON comparison also distinguishes false from 0 and true from 1.
            if json.dumps(declared, sort_keys=True) != json.dumps(expected, sort_keys=True):
                problems.append(f"fact {i} copied fields differ from the evidence DB")
    if cert.get("status") != "verified":
        problems.append("certificate is not marked verified")
    if not problems:
        expected_parts = [{"part": claims.to_json(part),
                           "english": claims.english(part, found, source),
                           "rules": claims.rules(part), "strength": claims.strength(part, found)}
                          for part in claims.parts(claim)]
        if cert.get("parts") != expected_parts:
            problems.append("part sentences or metadata differ from the generated claim")
        if cert.get("rules") != claims.rules(claim):
            problems.append("rule labels differ from the claim")
    if problems:
        return problems
    kernel = run_kernel(render_lean(cert["finding_id"], [found[i] for i in ids], claim),
                        cert["finding_id"])
    if not kernel["ok"]:
        problems.append("the Lean kernel does not accept the claim for these facts")
    elif kernel["tier"] != cert.get("trust_tier"):
        problems.append(f"trust tier is {kernel['tier']}, certificate says {cert.get('trust_tier')}")
    if kernel["ok"] and kernel["axioms"] != cert.get("axioms"):
        problems.append("declared axioms differ from the regenerated certificate")
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
