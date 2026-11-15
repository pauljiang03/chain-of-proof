"""Re-check a certificate without trusting the agent, the stored Lean file, or the report.

    python -m verifier.verify --run runs/current/run.json --facts evidence/case_facts.json

Three checks, all rebuilt from the evidence DB:
  1. every copied fact field and string still matches its DB row and row_sha256; for a census ("exactly n
     records of this kind") the cited facts must be every fact of that kind in the DB;
  2. the claim, regenerated as Lean from those rows, is accepted by the kernel;
  3. the English sentence, part sentences, rule/strength labels and axioms are exactly
     what regeneration produces for that claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import List

from checker import claims
from checker.check import render_lean, run_kernel, valid_finding_id
from checker.facts import FactSource, open_source


def verify(cert: dict, source: FactSource) -> List[str]:
    """Return the list of problems; empty means the certificate stands."""
    if not isinstance(cert, dict) or not valid_finding_id(cert.get("finding_id")):
        return ["finding id must look like F7 (letters, digits, _)"]
    problems: List[str] = []
    try:
        claim = claims.parse(cert["claim"])
    except claims.ClaimError as e:
        return [f"claim does not parse: {e}"]
    try:
        # for a census this is every fact of the kind now in the evidence: if the
        # certificate lists fewer or more, its count is about a different evidence file
        ids, found = claims.cited_facts(claim, source)
    except claims.ClaimError as error:
        # A failed census closure/type/capacity check cannot be replaced by the
        # explicitly named subset. In particular, never replay a partial set.
        return [f"cannot bind the complete cited evidence: {error}"]
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


def verify_run(run: dict, source: FactSource) -> dict:
    """Rebuild every certificate; reject malformed bundles and duplicate IDs."""
    findings = run.get("findings") if isinstance(run, dict) else None
    if not isinstance(findings, list):
        raise ValueError("run must contain a findings list")
    seen, checked = set(), []
    for cert in findings:
        fid = cert.get("finding_id") if isinstance(cert, dict) else None
        if not isinstance(fid, str) or not fid or fid in seen:
            raise ValueError("run contains missing or duplicate finding IDs")
        seen.add(fid)
        try:
            problems = verify(cert, source)
        except (ValueError, KeyError, TypeError) as error:
            problems = [str(error)]
        checked.append({"finding_id": fid, "problems": problems})
    failed = sum(bool(item["problems"]) for item in checked)
    return {"passed": failed == 0, "checked": len(checked),
            "verified": len(checked) - failed, "failed": failed, "findings": checked}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Re-check certificates against the evidence DB.")
    ap.add_argument("certs", nargs="*", help="certificate .json files")
    ap.add_argument("--run", help="one bundled run containing certificates")
    ap.add_argument("--out", help="new JSON verification result (with --run)")
    ap.add_argument("--facts", required=True, help="evidence DB (.duckdb) or fixture (.json)")
    args = ap.parse_args(argv)
    if bool(args.certs) == bool(args.run):
        ap.error("provide certificate files or --run")
    if args.out and not args.run:
        ap.error("--out requires --run")
    if args.out and (Path(args.out).exists() or Path(args.out).is_symlink()):
        ap.error("refusing to overwrite verification output")
    source = open_source(args.facts)
    if args.run:
        result = verify_run(json.loads(Path(args.run).read_text()), source)
        result.update(facts=args.facts,
                      facts_sha256=hashlib.sha256(Path(args.facts).read_bytes()).hexdigest(),
                      run=args.run,
                      run_sha256=hashlib.sha256(Path(args.run).read_bytes()).hexdigest())
        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            with Path(args.out).open("x") as stream:
                stream.write(json.dumps(result, indent=2) + "\n")
        print(f"{result['verified']}/{result['checked']} certificates verified; "
              f"{result['failed']} failed")
        for item in result["findings"]:
            for problem in item["problems"]:
                print(f"FAIL {item['finding_id']}: {problem}")
        return 0 if result["passed"] else 1
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
