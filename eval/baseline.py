"""The reproducible baseline run: miner findings plus the labeled false claims as probes.

    python3 -m eval.baseline --facts evidence/case_facts.json

Writes certs/ (every certificate and the full proposal log) and ui/public/run.json, then
scores the run. Outputs must be new paths; existing runs are never deleted.
Custom evidence requires an explicit reference and does not inherit NIST probes.
No LLM: the same evidence file always gives the same findings.

The labeled *true* claims are not part of the run. They were written with the answer key
open, so counting them as findings would inflate coverage. The labeled *false* claims are
included as probes: they can only add refusals.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agent.case import select_case
from checker import export
from checker.facts import open_source
from eval import score as scorer
from miner import mine as miner


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Run the deterministic baseline and score it.")
    ap.add_argument("--facts", default="evidence/case_facts.json")
    ap.add_argument("--certs", default="certs")
    ap.add_argument("--run", default="ui/public/run.json")
    ap.add_argument("--reference", help="answer key to score against (default: the open-book 10 questions)")
    gate = ap.add_mutually_exclusive_group()
    gate.add_argument("--labeled-claims", help="case-specific false-claim probes; legacy defaults apply only to original evidence")
    gate.add_argument("--no-gate", action="store_true", help="omit labeled-claim probes and gate scoring")
    ap.add_argument("--out", default="eval/results.json")
    ap.add_argument("--complete", action="store_true", help="include large one-record kinds and compound journal identity joins")
    args = ap.parse_args(argv)
    certs, run, output = Path(args.certs), Path(args.run), Path(args.out)
    try:
        profile, profile_source = select_case(Path(args.facts))
        if not args.reference and profile_source != "legacy":
            raise ValueError("nondefault facts require an explicit --reference")
        reference_path = Path(args.reference or scorer.REFERENCE)
        reference = json.loads(reference_path.read_text())
        zone = scorer.reference_zone(reference)
        gate_path = (None if args.no_gate else Path(args.labeled_claims) if args.labeled_claims else
                     scorer.LABELED if profile_source == "legacy" and scorer.is_nist_reference(reference)
                     else None)
        labeled = json.loads(gate_path.read_text()) if gate_path is not None else None
        if len({p.resolve() for p in (certs, run, output)}) != 3:
            raise ValueError("--certs, --run and --out must be distinct output paths")
        for path in (certs, run, output):
            if path.exists() or path.is_symlink():
                raise ValueError(f"refusing to overwrite existing output: {path}; choose a new path")
    except (ValueError, OSError) as exc:
        ap.error(str(exc))
    source = open_source(args.facts)
    skipped = miner.skipped_kinds(source, complete=args.complete)
    if skipped:
        print(f"bounded mode omits one-record statements for {skipped}; use --complete to include them")
        if set(skipped) & {"journalName", "journalParent", "journalRemoval"}:
            print("bounded mode also omits compound journal identity joins; --complete includes them")
    mined = miner.mine(source, certs, complete=args.complete)
    print(f"miner: {len(mined)} candidates, "
          f"{sum(r['status'] == 'verified' for r in mined)} certified")

    if labeled is not None:
        labeled["claims"] = [c for c in labeled["claims"] if not c["label"]]
        for n, c in enumerate(labeled["claims"], 1):
            # Gate fixture IDs may be arbitrary; keep output IDs distinct from miner M*.
            c["id"] = ("P" + c["id"][1:] if gate_path.resolve() == scorer.LABELED.resolve()
                       else f"P{n:03d}")
        probes = scorer.score_gate(labeled, source, scorer.rows_of(source),
                                   reference["tolerance_s"], out_dir=certs, time_zone=zone)
        print(f"probes: {len(probes)} false claims, "
              f"{sum(p['verdict'] == 'rejected' for p in probes)} refused")
    else:
        print("probes: not measured; no labeled claims selected for this case")

    run.parent.mkdir(parents=True, exist_ok=True)
    data = export.bundle(certs, profile.name)
    data["case"]["time_zone"] = profile.time_zone
    data["case"]["mining"] = {"complete": args.complete, "omitted_one_record_kinds": skipped}
    run.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"{run}: {len(data['findings'])} findings, {len(data['rejections'])} rejections\n")
    extra = ["--reference", str(reference_path)]
    extra += ["--labeled-claims", str(gate_path)] if gate_path is not None else ["--no-gate"]
    return scorer.main(["--facts", args.facts, "--run", str(run), "--out", args.out] + extra)


if __name__ == "__main__":
    sys.exit(main())
