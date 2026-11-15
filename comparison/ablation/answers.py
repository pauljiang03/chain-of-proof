"""Post-investigation scoring of A/C's literal, unverified final answer blocks.

Call only after the investigator has exited and its final summary is sealed.
Private references belong here, never in the investigation environment. B has
claim-retention metrics only; this module supplies no B answers or projector.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile

from agent.case import read_question_profile
from eval import benchmark, submission


_BLOCK = re.compile(r"(?ms)^```json\s*\n(.*?)^```\s*$")
_LIMITATIONS = [
    "Literal model answers are UNVERIFIED in both A and C; a Lean-accepted claim does not establish entailment of an answer value.",
    "This measures submitted answer agreement with the frozen reference, not independent forensic truth or claim correctness.",
    "B replays A's exact candidates for claim retention only; no B question accuracy or shared claim-to-answer projector is supplied.",
    "Missing or malformed answer blocks are unavailable measurements, not zero accuracy or fabricated unknown answers.",
    "All reference questions remain in the denominator; unresolved reference questions are not failed answers.",
]


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _constant(value):
    raise ValueError("non-finite JSON number")


def _json(raw):
    value = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_constant)
    # Also rejects finite-looking numeric literals that overflow to infinity.
    json.dumps(value, allow_nan=False)
    return value


def _read(path):
    path = Path(path)
    if path.is_symlink():
        raise ValueError("evaluation inputs cannot be symlinks")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(fd, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("evaluation inputs must be regular files")
        return stream.read()


def _contract(question_bytes, reference_bytes):
    public, reference = _json(question_bytes), _json(reference_bytes)
    if not isinstance(public, dict) or not isinstance(reference, dict):
        raise ValueError("public questions and private reference must be JSON objects")
    # Validate the exact in-memory snapshot with the existing public validator;
    # never reread a live input after recording its hash.
    with tempfile.TemporaryDirectory(prefix="cop-ablation-public-") as directory:
        path = Path(directory) / "questions.json"
        path.write_bytes(question_bytes)
        read_question_profile(path)
    benchmark.validate_reference(reference)
    if public["case_id"] != reference["case_id"]:
        raise ValueError("public and private case IDs differ")
    if public.get("time_zone") != reference.get("time_zone"):
        raise ValueError("public and private time zones differ")
    if public.get("contract_revision") != reference.get("public_contract_revision"):
        raise ValueError("public and private contract revisions differ")
    questions = {q["id"]: q for q in public["questions"]}
    if set(questions) != {q["id"] for q in reference["questions"]}:
        raise ValueError("public and private question IDs differ")
    for question in reference["questions"]:
        exposed = questions[question["id"]]
        if question["prompt"] != exposed["prompt"]:
            raise ValueError("public and private question prompts differ")
        if question.get("match", {}) != exposed.get("match", {}):
            raise ValueError("private matching rules differ from the public contract")
    return public, reference


def _denominator(reference):
    unresolved = [q["id"] for q in reference["questions"]
                  if q.get("evaluation", {}).get("status", "scorable") == "unevaluable"]
    transcription = reference.get("transcription")
    return {"total_questions": len(reference["questions"]),
            "scorable_questions": len(reference["questions"]) - len(unresolved),
            "unresolved_questions": len(unresolved), "unresolved_ids": unresolved,
            "review_status": reference.get("review_status"),
            "evaluation_use": reference.get("evaluation_use"),
            "independent_review_completed": (transcription.get("independent_review_completed")
                                             if isinstance(transcription, dict) else None),
            "note": "Scorable counts follow the frozen reference; provisional judgments are not upgraded by this evaluation."}


def _output_directory(out):
    path = Path(out).absolute()
    if ".." in path.parts:
        raise ValueError("evaluation output cannot contain parent traversal")
    for part in list(reversed(path.parents)) + [path]:
        if part.is_symlink():
            raise ValueError("evaluation output cannot traverse symlinks")
    if path.exists():
        raise FileExistsError("evaluation output already exists")
    path.mkdir(parents=True, exist_ok=False)
    return path


def _write(path, raw):
    with path.open("xb") as stream:
        stream.write(raw)


def _encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def evaluate_trial(summary_path, questions_path, reference_path, out, *, arm, expected_hashes):
    """Score one sealed A/C final summary identically, without facts or adapters.

    ``expected_hashes`` must contain exactly ``summary``, ``questions``, and
    ``reference``, each the sealed raw file's SHA-256. Setup/hash/contract errors
    raise before creating output. Missing or invalid answer blocks instead write
    an explicit unavailable result with ``score=None``. The new output directory
    contains byte-preserved summary/JSON block, separate provenance, and results.
    """
    if arm not in ("A", "C"):
        raise ValueError("literal question scoring is defined only for A and C; B has claim retention only")
    paths = {"summary": Path(summary_path), "questions": Path(questions_path), "reference": Path(reference_path)}
    if (not isinstance(expected_hashes, dict) or set(expected_hashes) != set(paths)
            or any(not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value)
                   for value in expected_hashes.values())):
        raise ValueError("expected_hashes must bind summary, questions, and reference SHA-256 values")
    snapshots = {name: _read(path) for name, path in paths.items()}
    for name, raw in snapshots.items():
        if _sha(raw) != expected_hashes[name]:
            raise ValueError(name + " hash differs from the sealed input")
    public, reference = _contract(snapshots["questions"], snapshots["reference"])
    reason, block, answer, score = None, None, None, None
    try:
        report = snapshots["summary"].decode("utf-8")
    except UnicodeError:
        reason = "Final summary is not valid UTF-8."
    else:
        blocks = _BLOCK.findall(report)
        if not blocks:
            reason = "Final summary has no fenced JSON answer block."
        elif len(blocks) != 1:
            reason = "Final summary must have exactly one fenced JSON block; no fallback block is selected."
        else:
            block = blocks[0].encode("utf-8")
            try:
                _json(block)
            except (ValueError, UnicodeError):
                reason = "Answer block is not strict finite JSON with unique object keys."
            else:
                try:
                    answer = submission.extract(report, public)
                except (ValueError, KeyError, TypeError):
                    reason = "Answer block does not satisfy the public submission contract; no answers were repaired."
                else:
                    # No arm-dependent transformation, evidence lookup, adapter,
                    # added provenance, status upgrade, or answer replacement.
                    try:
                        score = benchmark.score(reference, answer)
                    except (ValueError, KeyError, TypeError):
                        reason = "Answer block cannot be scored under the unchanged benchmark contract."
    measured = score is not None
    result = {"schema_version": 1, "arm": arm, "case_id": public["case_id"],
              "evaluation": {"measured": measured, "status": "measured" if measured else "unavailable",
                             "reason": reason, "metric": "literal_unverified_answer_agreement",
                             "answer_verification": "unverified", "claim_value_entailment": "not_established"},
              "reference_contract": _denominator(reference), "score": score,
              "provenance": "provenance.json", "limitations": list(_LIMITATIONS)}
    provenance = {"schema_version": 1, "arm": arm, "answer_verification": "unverified",
                  "method": "eval.submission.extract on the literal final model summary; no repair or adapter",
                  "claim_value_entailment": "not_established", "adapter": None,
                  "inputs": {name: {"path": str(paths[name].absolute()), "sha256": _sha(raw), "bytes": len(raw)}
                             for name, raw in snapshots.items()},
                  "software": {name: {"sha256": _sha(Path(path).read_bytes())} for name, path in (
                      ("evaluator", __file__), ("extractor", submission.__file__), ("scorer", benchmark.__file__))},
                  "submission_block_sha256": _sha(block) if block is not None else None,
                  "answers_sha256": _sha(block) if measured else None,
                  "summary_artifact": "summary.md", "block_artifact": "submission-block.txt" if block is not None else None,
                  "answers_artifact": "answers.json" if measured else None}
    # Serialize before creating output so unserializable input cannot leave a
    # plausible-looking half-result. Every artifact is written exclusively.
    encoded_result, encoded_provenance = _encoded(result), _encoded(provenance)
    output = _output_directory(out)
    _write(output / "summary.md", snapshots["summary"])
    if block is not None:
        _write(output / "submission-block.txt", block)
    if measured:
        _write(output / "answers.json", block)
    _write(output / "provenance.json", encoded_provenance)
    _write(output / "results.json", encoded_result)
    return result
