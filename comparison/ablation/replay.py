"""B: check every exact sealed A candidate once, with no investigator or repair.

Counts describe attempts, including duplicates. A refusal is not a ground-truth
forensic error. The original candidates remain separate from checker-normalized
certificates and are copied byte-for-byte, never rewritten or split.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import time

from checker import check as checker
from checker import claims
from checker.facts import open_source
from verifier.verify import verify

from .capture import CANDIDATES, SEAL, _binding, _decode, _encode, _regular, _rows


STATUSES = ("verified", "rejected", "malformed", "unsupported", "error")
LIMITATION = ("Counts describe checker outcomes for submitted whole claims, not ground-truth error labels. "
              "Refusal does not prove a forensic claim false; no answer projection or repair is performed.")


def _write(path, value):
    with Path(path).open("xb") as stream:
        stream.write(_encode(value) + b"\n")


def _digest(value, count=False):
    fields = {"sha256", "bytes"} | ({"file", "count"} if count else set())
    if (not isinstance(value, dict) or set(value) != fields
            or not isinstance(value.get("sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", value["sha256"]) is None
            or type(value.get("bytes")) is not int or value["bytes"] < 0):
        raise ValueError("Seal contains an invalid input binding.")
    if count and (value.get("file") != CANDIDATES
                  or type(value.get("count")) is not int or value["count"] < 0):
        raise ValueError("Seal must bind the fixed candidate log and its count.")


def _sealed(seal_path, facts_path):
    seal_path = Path(seal_path)
    if seal_path.name != SEAL:
        raise ValueError("Replay requires the fixed seal.json checkpoint.")
    with _regular(seal_path) as stream:
        seal_bytes = stream.read()
    seal = _decode(seal_bytes)
    if (not isinstance(seal, dict)
            or set(seal) != {"schema_version", "kind", "candidates", "facts", "metadata"}
            or type(seal.get("schema_version")) is not int or seal["schema_version"] != 1
            or seal.get("kind") != "ablation-candidate-seal"
            or not isinstance(seal.get("metadata"), dict)):
        raise ValueError("Unsupported candidate seal.")
    _digest(seal["candidates"], count=True)
    _digest(seal["facts"])
    # Never open a path from the manifest, even if a field resembles a filename.
    with _regular(seal_path.parent / CANDIDATES) as stream:
        raw = stream.read()
    expected = seal["candidates"]
    if len(raw) != expected["bytes"] or hashlib.sha256(raw).hexdigest() != expected["sha256"]:
        raise ValueError("Candidate bytes differ from the retained seal.")
    entries = _rows(raw)
    if len(entries) != expected["count"]:
        raise ValueError("Candidate count differs from the retained seal.")
    if _binding(facts_path) != seal["facts"]:
        raise ValueError("Replay facts differ from the sealed facts.")
    return seal, seal_bytes, raw, entries


def _categories(result):
    gap = result.get("proof_gap")
    requirements = gap.get("requirements", []) if isinstance(gap, dict) else []
    return sorted({item["category"] for item in requirements
                   if isinstance(item, dict) and isinstance(item.get("category"), str)})


def replay(seal_path, facts_path, out):
    """Replay the sealed log in a new directory and return its saved summary.

    All integrity/schema failures are refused before checking. A private exact
    facts snapshot binds checks and independent verification to one file. Per-call
    checker/verification exceptions remain explicit error attempts so one failure
    cannot silently remove later candidates. Interruptions are not swallowed.
    """
    seal_path, facts_path, out = Path(seal_path), Path(facts_path), Path(out)
    seal, seal_bytes, raw, entries = _sealed(seal_path, facts_path)
    if facts_path.suffix.lower() not in (".json", ".duckdb"):
        raise ValueError("Replay requires an extracted JSON or DuckDB facts file.")
    source_dir, destination = seal_path.parent.resolve(), out.resolve()
    if destination == source_dir or source_dir in destination.parents:
        raise ValueError("Replay output must be outside the source A run.")
    if out.exists() or out.is_symlink():
        raise FileExistsError("Replay output already exists.")
    out.mkdir(parents=True, exist_ok=False)
    (out / "source-seal.json").write_bytes(seal_bytes)
    (out / CANDIDATES).write_bytes(raw)
    facts_copy = out / ("facts" + facts_path.suffix.lower())
    with _regular(facts_path) as incoming, facts_copy.open("xb") as saved:
        shutil.copyfileobj(incoming, saved)
    if _binding(facts_copy) != seal["facts"]:
        raise ValueError("Facts changed while preparing the replay snapshot.")
    source = open_source(facts_copy)
    certificates = out / "certificates"
    certificates.mkdir()
    counts = {status: 0 for status in STATUSES}
    verification = {"checked": 0, "verified": 0, "failed": 0}
    accepted = []
    started = time.perf_counter_ns()
    try:
        with (out / "replay.jsonl").open("xb") as ledger:
            for candidate in entries:
                row = dict(candidate)
                row.update(status="error", checker_status=None, reason_categories=[],
                           verification=None, error=None)
                stage = "checker"
                tick = time.perf_counter_ns()
                try:
                    # The original value is passed directly, including strings,
                    # malformed structures, duplicates and entire conjunctions.
                    result = checker.check(candidate["claim"], candidate["candidate_id"], source,
                                           candidate["question"], out_dir=certificates, proposer="ablation:B")
                    row["checker_status"] = result.get("status")
                    row["reason_categories"] = _categories(result)
                    if result.get("status") == "verified":
                        stage = "independent_verification"
                        verification["checked"] += 1
                        cert_path = certificates / (candidate["candidate_id"] + ".json")
                        with _regular(cert_path) as stream:
                            cert = _decode(stream.read())
                        # Existing checker normalization is allowed only in the
                        # certificate. Bind it to this exact original whole claim.
                        expected = claims.to_json(claims.parse(candidate["claim"]))
                        problems = []
                        if (not isinstance(cert, dict) or cert.get("finding_id") != candidate["candidate_id"]
                                or _encode(cert.get("claim")) != _encode(expected)
                                or _encode(cert.get("question")) != _encode(candidate["question"])):
                            problems.append("Certificate does not bind the original candidate.")
                        else:
                            problems = verify(cert, source)
                        row["verification"] = {"passed": not problems, "problem_count": len(problems)}
                        if problems:
                            verification["failed"] += 1
                            row["error"] = {"stage": stage, "type": "CertificateVerificationError"}
                        else:
                            verification["verified"] += 1
                            row["status"] = "verified"
                            row["certificate"] = "certificates/" + candidate["candidate_id"] + ".json"
                            accepted.append(candidate["candidate_id"])
                    elif result.get("status") == "rejected":
                        categories = row["reason_categories"]
                        row["status"] = ("unsupported" if "unsupported_rule_or_form" in categories else
                                         "malformed" if "malformed_claim" in categories else "rejected")
                    else:
                        row["error"] = {"stage": stage, "type": "UnexpectedCheckerResult"}
                except Exception as error:
                    if stage == "independent_verification":
                        verification["failed"] += 1
                        row["verification"] = {"passed": False, "problem_count": None}
                    row["error"] = {"stage": stage, "type": type(error).__name__}
                row["duration_ns"] = time.perf_counter_ns() - tick
                counts[row["status"]] += 1
                ledger.write(_encode(row) + b"\n")
                ledger.flush()
    finally:
        if hasattr(source, "_db"):
            source._db.close()
    # Recheck the retained snapshots as well as A's original bytes. Replaying
    # never blesses a log or fact file that changed during this operation.
    if (_binding(facts_copy) != seal["facts"] or _binding(facts_path) != seal["facts"]
            or _binding(out / CANDIDATES) != {key: seal["candidates"][key] for key in ("sha256", "bytes")}
            or _binding(seal_path.parent / CANDIDATES) != {key: seal["candidates"][key] for key in ("sha256", "bytes")}
            or _binding(seal_path) != {"sha256": hashlib.sha256(seal_bytes).hexdigest(), "bytes": len(seal_bytes)}):
        raise ValueError("Sealed inputs changed during replay; no final summary was published.")
    summary = {"schema_version": 1, "kind": "ablation-offline-replay", "arm": "B", "source_arm": "A",
               "source_seal_sha256": hashlib.sha256(seal_bytes).hexdigest(),
               "candidates": seal["candidates"], "facts": seal["facts"],
               "total": len(entries), "counts": counts, "accepted_candidate_ids": accepted,
               "independent_verification": verification, "model_calls": 0,
               "duration_ns": time.perf_counter_ns() - started, "candidate_repair": False,
               "ground_truth_error_labels": False, "limitation": LIMITATION}
    _write(out / "summary.json", summary)
    return summary
