"""Freeze a small Sol-subagent pilot before either investigator sees the task.

The coordinator launches fresh subagents separately. This module never invokes a
model or provides the private reference to an investigator.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess

from agent.case import read_profile, read_question_profile, with_questions
from eval.benchmark import validate_reference

ROOT = Path(__file__).resolve().parents[2]
INPUTS = ("facts", "case_profile", "questions", "reference")
MODEL = "gpt-6.1-sol"


def fingerprint(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("Pilot inputs must be regular files, not symlinks")
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
            size += len(block)
    return {"path": str(path.resolve()), "sha256": digest.hexdigest(), "bytes": size}


def _json(path):
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    def constant(_):
        raise ValueError("Non-finite JSON number")

    value = json.loads(Path(path).read_text(), object_pairs_hook=pairs, parse_constant=constant)
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value


def _software():
    sources = {}
    for directory in ("agent", "checker", "verifier", "comparison/ablation"):
        for path in sorted((ROOT / directory).glob("*.py")):
            sources[str(path.relative_to(ROOT))] = fingerprint(path)["sha256"]
    for name in ("eval/benchmark.py", "eval/submission.py", "lean/lean-toolchain",
                 "lean/ChainOfProof.lean"):
        sources[name] = fingerprint(ROOT / name)["sha256"]
    for path in sorted((ROOT / "lean/ChainOfProof").glob("*.lean")):
        sources[str(path.relative_to(ROOT))] = fingerprint(path)["sha256"]
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True, check=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                               capture_output=True, text=True, check=True).stdout.strip())
    return {"commit": commit, "dirty": dirty, "source_sha256": sources,
            "python": platform.python_version(), "platform": platform.platform()}


def freeze_pilot(*, facts, case_profile, questions, reference, out, seconds=900):
    """Write one immutable-by-convention plan; return its contents and file hash."""
    if type(seconds) is not int or seconds <= 0:
        raise ValueError("The per-arm wall-time cap must be a positive integer")
    out = Path(out)
    if out.exists() or out.is_symlink():
        raise FileExistsError("Choose a new pilot output directory")
    paths = dict(facts=facts, case_profile=case_profile, questions=questions, reference=reference)
    bindings = {name: fingerprint(path) for name, path in paths.items()}
    public = read_question_profile(questions)
    with_questions(read_profile(case_profile), public)
    private = _json(reference)
    validate_reference(private)
    if private["case_id"] != public["case_id"] or private.get("time_zone") != public.get("time_zone"):
        raise ValueError("Public and private case contracts differ")
    if public.get("contract_revision") != private.get("public_contract_revision"):
        raise ValueError("Public and private contract revisions differ")
    expected = {str(q["id"]): q for q in private["questions"]}
    if {q["id"] for q in public["questions"]} != set(expected):
        raise ValueError("Public and private question IDs differ")
    for q in public["questions"]:
        other = expected[q["id"]]
        if q["prompt"] != other["prompt"] or q.get("match", {}) != other.get("match", {}):
            raise ValueError("Public and private question contracts differ")
    unresolved = [str(q["id"]) for q in private["questions"]
                  if q.get("evaluation", {}).get("status") == "unevaluable"]
    manifest = {
        "schema_version": 1, "protocol": "sol-subagent-A-C-answer-pilot-and-A-B-claim-filter",
        "created_at": datetime.now(timezone.utc).isoformat(), "frozen_before_trials": True,
        "evaluation_use": "development_not_blind", "replicates": 1, "order": ["A", "C", "B"],
        "inputs": bindings, "software": _software(),
        "case": {"case_id": public["case_id"], "questions": len(public["questions"]),
                 "provisionally_scorable": len(public["questions"]) - len(unresolved),
                 "unevaluable_ids": unresolved, "reference_status": private.get("review_status", "unknown")},
        "model": {"requested_override": MODEL, "fresh_context": "fork_turns=none",
                  "observed_model_id": None, "immutable_revision": None,
                  "reasoning_effort": "same inherited platform default; not independently observed"},
        "budget": {"wall_seconds_per_live_arm": seconds, "model_tokens": None,
                   "model_cost": None, "token_and_cost_comparability": "unavailable",
                   "B_model_calls": 0, "extra_budget_after_failure": False},
        "arms": {"A": "receipt-only unchecked proposals; no semantic feedback",
                 "C": "online checker feedback and independently replayable certificates",
                 "B": "offline exact whole-candidate replay of sealed A; no answer score"},
        "measurements": {
            "answer_accuracy": "A/C literal model JSON, identical deterministic scoring; both answer blocks unverified",
            "claim_filtering": "A-to-B retention/refusal/error counts; refusal does not establish a forensic error",
            "candidate_population": "JSON object claims admitted by the shared transport schema; malformed object contents remain exact candidates, transport rejections are separate",
            "shared_claim_faithful_projector": "not implemented; no B question-accuracy claim",
            "reference_policy": "Retain frozen draft reference; unresolved questions remain visible and unscored",
            "missing_output_policy": "Retain failures/timeouts; invalid or absent submission is unmeasured, not repaired",
            "claims_allowed": "single development pilot; no statistical significance, universal precision or end-to-end speed claim"},
        "isolation": {"mode": "procedural instructions, not an OS sandbox",
                      "allowed_reads": "assigned public brief and the four forms/sql/fact/check bridge tools",
                      "forbidden": ["private references", "prior reports", "repository browsing", "other agents", "web"],
                      "bridge_audit": "retain tool requests/results and final answer",
                      "platform_tool_trace": "retain when exposed; unavailable traces do not establish full compliance"},
        "preparation": {"facts": "same existing extracted snapshot for both arms",
                        "fresh_extraction_seconds": None, "end_to_end_extraction_comparison": False},
    }
    # Refuse input changes observed while the contracts were inspected.
    if any(fingerprint(path) != bindings[name] for name, path in paths.items()):
        raise ValueError("An input changed during pilot preparation")
    out.mkdir(parents=True, exist_ok=False)
    path = out / "frozen-manifest.json"
    with path.open("x") as stream:
        json.dump(manifest, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    return {"manifest": manifest, "manifest_sha256": fingerprint(path)["sha256"]}


def validate_frozen(path, *, expected_sha256):
    """Recheck retained checkpoint, input bytes and code before execution/scoring."""
    if fingerprint(path)["sha256"] != expected_sha256:
        raise ValueError("Frozen manifest differs from the retained checkpoint")
    manifest = _json(path)
    if manifest.get("schema_version") != 1 or set(manifest.get("inputs", {})) != set(INPUTS):
        raise ValueError("Unsupported frozen pilot manifest")
    for binding in manifest["inputs"].values():
        if fingerprint(binding["path"]) != binding:
            raise ValueError("A frozen pilot input changed")
    if manifest["software"]["source_sha256"] != _software()["source_sha256"]:
        raise ValueError("Frozen implementation changed")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--facts", required=True)
    parser.add_argument("--case-profile", required=True)
    parser.add_argument("--questions", required=True)
    parser.add_argument("--reference", required=True, help="coordinator-only private scoring contract")
    parser.add_argument("--out", required=True)
    parser.add_argument("--seconds", type=int, default=900)
    args = parser.parse_args(argv)
    try:
        result = freeze_pilot(facts=args.facts, case_profile=args.case_profile, questions=args.questions,
                              reference=args.reference, out=args.out, seconds=args.seconds)
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.error(str(error))
    print(json.dumps({"manifest_sha256": result["manifest_sha256"], "output": str(Path(args.out).resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
