"""The written report of a run: what an investigator is handed.

    python3 -m checker.report runs/current/run.json > report.md

Certified findings by default; an explicitly requested appendix stays separate:

  Findings      sentences the proof checker generated and certified from records, with
                their strength, rules and the artifacts they cite.
  Appendix      optional investigator inferences. Not checked. Each names the certified
                findings it rests on; those citations do not certify the inference.

Nothing is reworded: every finding is the certificate's sentence as written.
"""
from __future__ import annotations

import json
import argparse
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


def render(run: dict, include_judgments: bool = False) -> str:
    L = [f"# Investigation report: {run['case']['name']}", ""]
    stats = run["stats"]
    L += [f"{stats['verified']} findings certified by the proof checker, {stats['rejected']} "
          "proposed claims refused.", ""]
    if include_judgments:
        L += [f"{len(run.get('conclusions', []))} unverified judgments are included in a "
              "separate appendix at the reader's explicit request.", ""]
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
    if not include_judgments:
        return "\n".join(L) + "\n"
    L += ["## Appendix: unverified investigator conclusions (outside Lean)", "",
          "These are the investigator's judgments, not certified results. Citing certified "
          "findings does not verify an inference, a causal claim, or a device attribution. "
          "The token and consistency checks are limited safeguards, not proofs.", ""]
    for c in run.get("conclusions", []):
        weak = " Rests in part on a heuristic finding." if c.get("rests_on_heuristic") else ""
        L.append(f"- **{c['conclusion_id']}** (inference, unverified) {c['text']} "
                 f"[rests on {', '.join(c['finding_ids'])}]{weak}")
    if not run.get("conclusions"):
        L.append("- none recorded")
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Render certified findings; judgments are opt-in.")
    ap.add_argument("run")
    ap.add_argument("--include-judgments", action="store_true",
                    help="append unverified AI judgments, outside the certified report")
    args = ap.parse_args(argv)
    sys.stdout.write(render(json.loads(Path(args.run).read_text()), args.include_judgments))
    return 0


if __name__ == "__main__":
    sys.exit(main())
