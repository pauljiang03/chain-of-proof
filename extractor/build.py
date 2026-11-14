"""Build the evidence file from the case images.

    uv run --extra extract python -I extractor/build.py data --out evidence/case_facts.json

Reads the images named in extractor/exhibits.json from the given directory. Output is
the same JSON shape as fixtures/sample_facts.json, so `--facts evidence/case_facts.json`
works everywhere the fixture does. Add --duckdb PATH to also write the SQL database.
Same images in, same file out: rows are sorted before ids are assigned.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))   # run with `python -I`: the repo root is added explicitly

from extractor.media import extract_media          # noqa: E402
from extractor.store import Evidence, us           # noqa: E402
from extractor.tags import add_tags                # noqa: E402
from extractor.windows import extract_pc           # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Extract facts from the case images.")
    ap.add_argument("images", help="directory holding pc.E01, rm1.E01, rm2.E01")
    ap.add_argument("--out", default=str(ROOT / "evidence" / "case_facts.json"))
    ap.add_argument("--duckdb", help="also write a DuckDB evidence database here")
    ap.add_argument("--examined-at", default="2026-11-14T00:00:00+00:00",
                    help="timestamp given to facts that are observations, not events")
    args = ap.parse_args(argv)

    images = Path(args.images)
    exhibits = json.loads((ROOT / "extractor" / "exhibits.json").read_text())
    examined_at = us(datetime.fromisoformat(args.examined_at).astimezone(timezone.utc))
    tool = f"dissect.target {version('dissect.target')}"
    ev, log, info = Evidence(), [], {}

    pc = next((n for n, e in exhibits.items() if isinstance(e, dict) and e.get("role") == "pc"), None)
    if pc and (images / pc).exists():
        info, lines = extract_pc(ev, images / pc, tool)
        log += lines
    fat_tz = info.get("time_zone") or "UTC"
    for name, exhibit in exhibits.items():
        if isinstance(exhibit, dict) and exhibit.get("role") == "removable" and (images / name).exists():
            log += extract_media(ev, images / name, exhibit, fat_tz, examined_at, tool)
    tags = add_tags(ev, examined_at)

    meta = ev.write_json(args.out, {
        "case": "NIST CFReDS Data Leakage Case",
        "images": sorted(p.name for p in images.glob("*.E0*")),
        "pc": info, "fat_time_zone": fat_tz, "examined_at": args.examined_at, "tool": tool,
        "note": "Extracted from the real images. Regenerate with extractor/build.py.",
    })
    if args.duckdb:
        ev.write_duckdb(args.duckdb, (ROOT / "extractor" / "schema.sql").read_text())
    for line in log:
        print(line)
    print(f"{tags} tags")
    for line in meta["unparsed"]:
        print("could not parse:", line)
    print(f"{args.out}: {meta['facts']} facts {meta['by_kind']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
