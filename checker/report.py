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

from . import citations


def _proof_gaps(run: dict) -> list:
    gaps = [(r, r.get("proof_gap")) for r in run.get("rejections", [])
            if isinstance(r.get("proof_gap"), dict) and r["proof_gap"].get("status") == "diagnostic"]
    if not gaps:
        return []
    lines = ["## Not established / further evidence needed", "",
             "These are diagnostics for refused proposals, not certified findings. "
             "Refusal does not establish that a proposed claim is false. Suggested evidence "
             "does not establish that the claim will become provable.", ""]
    for rejection, gap in gaps:
        lines += [f"- **{citations.value(rejection, 'finding_id')}** (diagnostic, not certified): "
                  f"{citations.value(gap, 'summary')}"]
        for requirement in gap.get("requirements") or []:
            if not isinstance(requirement, dict):
                continue
            lines += [f"  - **{citations.value(requirement, 'category')}**: {citations.value(requirement, 'reason')}",
                      f"    Further evidence or action: {citations.value(requirement, 'action')}."]
            for key, label in (("fact_ids", "Fact IDs"), ("observed", "Observed"), ("required", "Required condition")):
                if key in requirement:
                    lines.append(f"    {label}: {citations.text(json.dumps(requirement[key], sort_keys=True, ensure_ascii=False))}.")
        if gap.get("disclaimer"):
            lines.append("  " + citations.text(gap["disclaimer"]))
    return lines + [""]


def render(run: dict, include_judgments: bool = False) -> str:
    L = [f"# Investigation report: {citations.text(run['case']['name'])}", ""]
    stats = run["stats"]
    L += [f"{citations.value(stats, 'verified')} findings certified by the proof checker, {citations.value(stats, 'rejected')} "
          "proposed claims refused.", ""]
    if include_judgments:
        L += [f"{len(run.get('conclusions', []))} unverified judgments are included in a "
              "separate appendix at the reader's explicit request.", ""]
    L += ["", "## Certified findings", "",
          "Each sentence was generated from extracted records and checked by the proof "
          "checker. `strong`: follows from what the artifacts record. `heuristic`: rests on "
          "a stated rule of thumb. Sentences are reproduced without rewording; markup is "
          "escaped for display. This renderer does not independently verify certificates.", ""]
    by_q = OrderedDict()
    for number, f in enumerate(run["findings"], 1):
        by_q.setdefault(f.get("question") or "(no question given)", []).append((number, f))
    for q, items in by_q.items():
        L += [f"### {citations.text(q)}", ""]
        for number, f in items:
            links = [f"[fact {citations.value(row, 'id')}](#evidence-f{number}-r{index})"
                     for index, row in enumerate(f.get("cited_facts", []), 1)]
            evidence = ", ".join(links) if links else "No copied evidence records were included."
            L.append(f"- **{citations.value(f, 'finding_id')}** ({citations.value(f, 'strength')}; "
                     f"rules {citations.text(', '.join(map(str, f.get('rules', []))))}) "
                     f"{citations.value(f, 'english')} Evidence: {evidence} "
                     f"[Proof record](#proof-f{number}).")
        L.append("")
    L += _proof_gaps(run)
    L += ["## Evidence records", "",
          "Every copied citation is shown below, scoped to its finding. Repeated fact IDs "
          "are not merged. Provenance is copied metadata; its presence does not prove the "
          "parser or its interpretation correct. Source offsets and locations appear only "
          "when supplied by the record.", ""]
    conflicts = citations.conflicting_fact_ids(run["findings"])
    for number, f in enumerate(run["findings"], 1):
        for index, row in enumerate(f.get("cited_facts", []), 1):
            L += citations.evidence_record(f, row, number, index, conflicts)
    L += ["## Proof records", "",
          "These are the bundle's declared claims and embedded proofs. To verify them, use "
          "the independent verifier with the original evidence store.", ""]
    for number, f in enumerate(run["findings"], 1):
        L += citations.proof_record(f, number)
    if not include_judgments:
        return "\n".join(L) + "\n"
    L += ["## Appendix: unverified investigator conclusions (outside Lean)", "",
          "These are the investigator's judgments, not certified results. Citing certified "
          "findings does not verify an inference, a causal claim, or a device attribution. "
          "The token and consistency checks are limited safeguards, not proofs.", ""]
    for c in run.get("conclusions", []):
        weak = " Rests in part on a heuristic finding." if c.get("rests_on_heuristic") else ""
        L.append(f"- **{citations.value(c, 'conclusion_id')}** (inference, unverified) {citations.value(c, 'text')} "
                 f"(rests on {citations.text(', '.join(map(str, c['finding_ids'])))}){weak}")
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
