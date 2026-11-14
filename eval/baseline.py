"""The reproducible baseline run: miner findings plus the labeled false claims as probes.

    python3 -m eval.baseline --facts evidence/case_facts.json

Writes certs/ (every certificate and the full proposal log) and ui/public/run.json, then
scores the run. No LLM: the same evidence file always gives the same findings.

The labeled *true* claims are not part of the run. They were written with the answer key
open, so counting them as findings would inflate coverage. The labeled *false* claims are
included as probes: they can only add refusals.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

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
    ap.add_argument("--out", default="eval/results.json")
    args = ap.parse_args(argv)
    certs = Path(args.certs)
    if certs.exists():
        shutil.rmtree(certs)
    source = open_source(args.facts)
    mined = miner.mine(source, certs)
    print(f"miner: {len(mined)} candidates, "
          f"{sum(r['status'] == 'verified' for r in mined)} certified")

    reference = json.loads(Path(args.reference or scorer.REFERENCE).read_text())
    labeled = json.loads(scorer.LABELED.read_text())
    labeled["claims"] = [c for c in labeled["claims"] if not c["label"]]
    for c in labeled["claims"]:
        c["id"] = "P" + c["id"][1:]
    probes = scorer.score_gate(labeled, source, scorer.rows_of(source),
                               reference["tolerance_s"], out_dir=certs)
    print(f"probes: {len(probes)} false claims, "
          f"{sum(p['verdict'] == 'rejected' for p in probes)} refused")

    run = Path(args.run)
    run.parent.mkdir(parents=True, exist_ok=True)
    data = export.bundle(certs, "NIST CFReDS Data Leakage Case")
    run.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"{run}: {len(data['findings'])} findings, {len(data['rejections'])} rejections\n")
    extra = ["--reference", args.reference] if args.reference else []
    return scorer.main(["--facts", args.facts, "--run", str(run), "--out", args.out] + extra)


if __name__ == "__main__":
    sys.exit(main())
