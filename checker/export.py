"""Bundle a run into one JSON file for the front end.

    python -m checker.export --certs certs --out ui/public/run.json

The front end reads only this file. Shape:

    {
      "version": 1,
      "case": {"name": ..., "generated_at": ...},
      "stats": {"proposals", "verified", "rejected", "by_strength": {...}, "by_rule": {...}},
      "findings":   [certificate, ...],      # verified, each with "lean" source attached
      "rejections": [rejected proposal, ...] # with the failing bricks named
    }

A certificate is exactly what check() returns for a verified claim; see
fixtures/sample_cert/N1.json. Nothing here is recomputed or reworded.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def bundle(certs_dir: Path, case_name: str) -> dict:
    certs_dir = Path(certs_dir)
    findings = []
    for path in sorted(certs_dir.glob("*.json")):
        cert = json.loads(path.read_text())
        if cert.get("status") != "verified":
            continue
        lean = certs_dir / cert.get("lean_file", "")
        cert["lean"] = lean.read_text() if lean.is_file() else ""
        findings.append(cert)
    proposals = []
    log = certs_dir / "proposals.jsonl"
    if log.is_file():
        proposals = [json.loads(line) for line in log.read_text().splitlines() if line.strip()]
    rejections = [p for p in proposals if p.get("status") == "rejected"]
    return {
        "version": 1,
        "case": {"name": case_name,
                 "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},
        "stats": {
            "proposals": len(proposals),
            "verified": sum(p.get("status") == "verified" for p in proposals),
            "rejected": len(rejections),
            "by_strength": dict(Counter(f["strength"] for f in findings)),
            "by_rule": dict(Counter(r for f in findings for r in f["rules"])),
        },
        "findings": findings,
        "rejections": rejections,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Bundle certificates for the front end.")
    ap.add_argument("--certs", default="certs")
    ap.add_argument("--out", required=True)
    ap.add_argument("--case", default="NIST CFReDS Data Leakage Case")
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    data = bundle(Path(args.certs), args.case)
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"{out}: {len(data['findings'])} findings, {len(data['rejections'])} rejections")
    return 0


if __name__ == "__main__":
    sys.exit(main())
