"""Bundle a run into one JSON file for the front end.

    python -m checker.export --certs certs --out ui/public/run.json

The front end reads only this file. Shape:

    {
      "version": 1,
      "case": {"name": ..., "generated_at": ...},
      "stats": {"proposals", "verified", "rejected", "by_strength": {...}, "by_rule": {...}},
      "findings":   [certificate, ...],      # verified, each with "lean" source attached
      "rejections": [rejected proposal, ...] # with the failing bricks named
      "conclusions": [{conclusion_id, text, finding_ids, strength: "judgment", note}, ...]
    }

Conclusions are the investigator's own inferences. They are not checked by the kernel
and must never be shown as findings: see agent/conclusions.py.

A certificate is exactly what check() returns for a verified claim; see
fixtures/sample_cert/N1.json. Nothing here is recomputed or reworded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def _sidecar(directory, name):
    path = directory / name
    if path.is_symlink():
        raise ValueError(f"run sidecar cannot be a symlink: {name}")
    return json.loads(path.read_text()) if path.is_file() else None


def _audit_snapshot(directory, expected_head):
    """Verify exactly the bytes summarized, even if a live log later grows."""
    from agent.audit import LIMITATION, verify_audit

    path = directory / "audit.jsonl"
    summary = {"status": "unavailable", "path": None, "passed": None,
               "count": None, "head": None, "sha256": None,
               "expected_head": expected_head, "problems": [], "scope": LIMITATION}
    if not path.exists() and not path.is_symlink() and expected_head is None:
        return summary, None
    summary.update(status="invalid", path="audit.jsonl", passed=False)
    if path.is_symlink():
        summary["problems"] = ["audit log cannot be a symlink"]
        return summary, []
    try:
        raw = path.read_bytes()
    except OSError as error:
        summary["problems"] = ["cannot read audit: " + type(error).__name__]
        return summary, []
    summary["sha256"] = hashlib.sha256(raw).hexdigest()
    # verify_audit accepts a path. An immutable snapshot prevents checking one
    # version of an actively appended log and summarizing another version.
    with tempfile.TemporaryDirectory(prefix="cop-export-audit-") as temporary:
        snapshot = Path(temporary) / "audit.jsonl"
        snapshot.write_bytes(raw)
        result = verify_audit(snapshot, expected_head=expected_head)
    summary.update({key: result[key] for key in ("passed", "count", "head", "problems")})
    summary["status"] = "valid" if result["passed"] else "invalid"

    def reject_constant(value):
        raise ValueError("non-finite audit JSON number")

    try:
        events = [json.loads(line, parse_constant=reject_constant) for line in raw.splitlines()]
    except (ValueError, UnicodeError):
        events = []
    return summary, events


def bundle(certs_dir: Path, case_name: str, *, facts_metadata=None,
           public_questions=None, answers=None, health=None, audit_expected_head=None,
           case_metadata=None) -> dict:
    """Keep certificate fields intact and add separately qualified run metadata.

    Inputs are public extraction metadata/questions/answers, never a reference.
    Optional fixed sidecars are used only when the corresponding value is absent.
    Missing logs are unmeasured, not evidence that no tool calls occurred.
    Case metadata is merged before coverage evaluates execution and question scope.
    Certificates need a verified proposal entry or a same-ID Lean artifact; unrelated
    JSON files are never opened to discover certificates.
    """
    from agent.coverage import summarize_coverage
    from agent.history import summarize_history
    from checker.check import valid_finding_id

    certs_dir = Path(certs_dir)
    log = certs_dir / "proposals.jsonl"
    if log.is_symlink():
        raise ValueError("proposal log cannot be a symlink")
    proposals = ([json.loads(line) for line in log.read_text().splitlines() if line.strip()]
                 if log.is_file() else [])
    # Generated certificates have a same-ID Lean file or an entry in the fixed
    # proposal log. Do not scan unrelated JSON (answers, references, or secrets).
    identifiers = {p.get("finding_id") for p in proposals if isinstance(p, dict)
                   and p.get("status") == "verified" and valid_finding_id(p.get("finding_id"))}
    identifiers.update(p.stem for p in certs_dir.glob("*.lean") if valid_finding_id(p.stem))
    findings = []
    for identifier in sorted(identifiers):
        path = certs_dir / (identifier + ".json")
        if path.is_symlink():
            raise ValueError(f"run artifact cannot be a symlink: {path.name}")
        if not path.is_file():
            continue
        cert = json.loads(path.read_text())
        if not isinstance(cert, dict) or cert.get("status") != "verified":
            continue
        if cert.get("finding_id") != identifier:
            raise ValueError("certificate finding ID differs from its artifact name")
        lean_name = cert.get("lean_file", "")
        if not isinstance(lean_name, str) or (lean_name and (
                Path(lean_name).name != lean_name or "\\" in lean_name
                or Path(lean_name).suffix != ".lean")):
            raise ValueError("certificate Lean source must name a local .lean file")
        lean = certs_dir / lean_name
        if lean.is_symlink():
            raise ValueError("certificate Lean source cannot be a symlink")
        cert["lean"] = lean.read_text() if lean.is_file() else ""
        findings.append(cert)
    rejections = [p for p in proposals if p.get("status") == "rejected"]
    conclusions = []
    notes = certs_dir / "conclusions.jsonl"
    if notes.is_symlink():
        raise ValueError("conclusion log cannot be a symlink")
    if notes.is_file():
        conclusions = [json.loads(line) for line in notes.read_text().splitlines() if line.strip()]
    data = {
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
        # the investigator's judgment: NOT checked by the kernel, each cites certified findings
        "conclusions": conclusions,
    }
    if case_metadata is not None:
        if not isinstance(case_metadata, dict):
            raise ValueError("case metadata must be an object")
        data["case"].update(case_metadata)
    audit, events = _audit_snapshot(certs_dir, audit_expected_head)
    if facts_metadata is None:
        facts_metadata = _sidecar(certs_dir, "extraction-metadata.json")
    if public_questions is None:
        public_questions = _sidecar(certs_dir, "questions.json")
    data["audit"] = audit
    verification = audit if audit["status"] != "unavailable" else None
    data["coverage"] = summarize_coverage(data, facts_metadata=facts_metadata,
        audit_events=events, public_questions=public_questions, answers=answers,
        health=health, audit_verification=verification)
    data["history"] = summarize_history(proposals if log.is_file() else None,
        audit_events=events, audit_verification=verification)
    manifest = _sidecar(certs_dir, "run-manifest.json")
    if manifest is not None:
        if not isinstance(manifest, dict):
            raise ValueError("recorded run manifest must be an object")
        data["run_manifest"] = manifest
    from agent.answers import enrich_bundle
    enrich_bundle(data, certs_dir, public_questions=public_questions)
    review = _sidecar(certs_dir, "review.json")
    if review is not None:
        if (not isinstance(review, dict) or review.get("schema_version") != 1
                or review.get("status") not in ("diagnostic", "unavailable") or not isinstance(review.get("scope"), dict)
                or not isinstance(review.get("diagnostics"), list)
                or any(not isinstance(item, dict) or item.get("status") != "diagnostic"
                       for item in review["diagnostics"])):
            raise ValueError("conflict review must contain schema-v1 diagnostic records")
        data["conflicts"] = review  # diagnostic only; never a finding or certificate
    continuation = _sidecar(certs_dir, "continuation.json")
    if continuation is not None:
        if (not isinstance(continuation, dict) or continuation.get("schema_version") != 1
                or type(continuation.get("same_evidence")) is not bool
                or continuation.get("replay_log") != "continuation-replay.json"
                or not isinstance(continuation.get("parent"), str)):
            raise ValueError("continuation must contain a schema-v1 recorded parent binding")
        data["continuation"] = continuation
    replay = _sidecar(certs_dir, "continuation-replay.json")
    if replay is not None:
        if (continuation is None or not isinstance(replay, dict) or replay.get("schema_version") != 1
                or not isinstance(replay.get("replayed"), list)):
            raise ValueError("continuation replay requires a parent binding and schema-v1 replay records")
        data["continuation_replay"] = replay
    collection = _sidecar(certs_dir, "latest-collection.json")
    if collection is not None:
        if not isinstance(collection, dict) or not isinstance(collection.get("facts"), str) or collection.get("continuation_required") is not True:
            raise ValueError("collection must be a successful new-snapshot receipt")
        data["collection"] = collection
    return data


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
