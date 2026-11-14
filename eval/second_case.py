"""Score the pipeline on a case it was not built on.

    python3 -m eval.second_case                 # extraction only
    python3 -m eval.second_case --mine          # also run the miner and count certified rows

The case is "The Stolen Szechuan Sauce" (DFIR Madness, case 001), desktop disk image
only. Its evidence file (eval/case2/case_facts.json) was produced by the readers as
they stood after the NIST case, with one change: the first reader crashed on a PC that
has no USB registry key, and now reports a missing artifact and goes on.

The reference (eval/case2/reference.json) was transcribed from the case author's
published answers by an agent that never saw the readers or their output. Each row
says where its evidence lives (`needs`). Only rows that need the desktop disk are a
fair target for a desktop-disk pipeline; the others are listed, not hidden.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import OrderedDict
from pathlib import Path

from checker import export
from checker.facts import open_source
from eval import score as scorer
from miner import mine as miner

ROOT = Path(__file__).resolve().parent.parent
CASE = ROOT / "eval" / "case2"
STATUSES = ("match", "time_differs", "missing", "not_expressible")


def table(reference: dict, extraction, certified=None) -> str:
    needs = {i["id"]: i.get("needs", "unstated") for i in reference["items"]}
    groups = OrderedDict()
    for e in extraction:
        g = groups.setdefault(needs[e["id"]], {s: 0 for s in STATUSES + ("rows", "certified")})
        g["rows"] += 1
        g[e["status"]] += 1
        if certified and e["id"] in certified:
            g["certified"] += 1
    L = [f"   {'evidence the answer needs':<28}{'rows':>5}{'match':>7}{'time off':>10}{'missing':>9}"
         f"{'no kind':>9}" + (f"{'certified':>11}" if certified is not None else "")]
    for name, g in groups.items():
        L.append(f"   {name:<28}{g['rows']:>5}{g['match']:>7}{g['time_differs']:>10}{g['missing']:>9}"
                 f"{g['not_expressible']:>9}" + (f"{g['certified']:>11}" if certified is not None else ""))
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Score the second, unseen case.")
    ap.add_argument("--facts", default=str(CASE / "case_facts.json"))
    ap.add_argument("--reference", default=str(CASE / "reference.json"))
    ap.add_argument("--mine", action="store_true", help="run the miner and count certified rows")
    ap.add_argument("--out", default=str(CASE / "results.json"))
    args = ap.parse_args(argv)
    source = open_source(args.facts)
    rows = scorer.rows_of(source)
    reference = json.loads(Path(args.reference).read_text())
    extraction = scorer.score_extraction(reference, rows)
    results = {"facts": len(rows), "reference_rows": len(reference["items"]), "extraction": extraction}
    certified = None
    if args.mine:
        certs = ROOT / "runs" / "case2-miner"
        if certs.exists():
            shutil.rmtree(certs)
        mined = miner.mine(source, certs)
        run = export.bundle(certs, "The Stolen Szechuan Sauce, desktop disk")
        scored = scorer.score_run(reference, run)
        certified = {i["id"] for i in scored["items"] if i["certified"]}
        results["run"] = {"proposals": len(mined), "verified": run["stats"]["verified"],
                          "rejected": run["stats"]["rejected"], "certified_rows": sorted(certified)}
        print(f"miner: {len(mined)} claims proposed, {run['stats']['verified']} certified, "
              f"{run['stats']['rejected']} refused")
    Path(args.out).write_text(json.dumps(results, indent=1, ensure_ascii=False) + "\n")
    print(f"Second case: {len(rows)} records, {len(reference['items'])} answer rows\n")
    print(table(reference, extraction, certified))
    return 0


if __name__ == "__main__":
    sys.exit(main())
