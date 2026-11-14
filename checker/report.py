"""The written report of a run: what an investigator is handed.

    python3 -m checker.report runs/investigator/run.json > report.md

Two parts, never mixed:

  Conclusions   the investigator's own inferences. Not checked. Each names the certified
                findings it rests on.
  Findings      sentences the proof checker generated and certified from records, with
                their strength, rules and the artifacts they cite.

Nothing is reworded: every finding is the certificate's sentence as written.
"""
from __future__ import annotations

import json
import sys
from collections import OrderedDict
from pathlib import Path


def _artifacts(finding: dict, most: int = 2) -> str:
    seen = OrderedDict()
    for c in finding.get("cited_facts", []):
        prov = c.get("prov", {})
        where = " / ".join(str(prov[k]) for k in ("exhibit", "artifact") if prov.get(k))
        if where:
            seen.setdefault(where, None)
    names = list(seen)
    more = f" (+{len(names) - most} more)" if len(names) > most else ""
    return "; ".join(names[:most]) + more


def render(run: dict) -> str:
    L = [f"# Investigation report: {run['case']['name']}", ""]
    stats = run["stats"]
    L += [f"{stats['verified']} findings certified by the proof checker, {stats['rejected']} "
          f"proposed claims refused, {len(run.get('conclusions', []))} conclusions.", ""]
    L += ["## Conclusions (judgment: inferences, NOT verified)", "",
          "These are the investigator's inferences. The proof checker has not verified them "
          "and cannot. Each rests on the certified findings named after it.", ""]
    for c in run.get("conclusions", []):
        weak = " Rests in part on a heuristic finding." if c.get("rests_on_heuristic") else ""
        L.append(f"- **{c['conclusion_id']}** (inference, unverified) {c['text']} "
                 f"[rests on {', '.join(c['finding_ids'])}]{weak}")
    if not run.get("conclusions"):
        L.append("- none recorded")
    L += ["", "## Certified findings", "",
          "Each sentence was generated from extracted records and checked by the proof "
          "checker. `strong`: follows from what the artifacts record. `heuristic`: rests on "
          "a stated rule of thumb.", ""]
    by_q = OrderedDict()
    for f in run["findings"]:
        by_q.setdefault(f.get("question") or "(no question given)", []).append(f)
    for q, items in by_q.items():
        L += [f"### {q}", ""]
        for f in items:
            L.append(f"- **{f['finding_id']}** ({f['strength']}; rules {', '.join(f['rules'])}) "
                     f"{f['english']} Evidence: {_artifacts(f)}.")
        L.append("")
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    path = (argv or sys.argv[1:])[0]
    sys.stdout.write(render(json.loads(Path(path).read_text())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
