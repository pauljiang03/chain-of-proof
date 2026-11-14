"""Prepare public inputs for an external investigation. Never launch a model.

    python -m eval.package --questions eval/benchmark_nist_questions.json \
        --images data/pc.E01 data/pc.E02 data/pc.E03 data/pc.E04 \
        data/rm1.E01 data/rm2.E01 data/rm3.E01 --out comparison/mulder
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from agent.case import read_profile, read_question_profile, with_questions


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def prepare(questions, images, out, case_profile=None):
    public = read_question_profile(Path(questions))
    context = read_profile(Path(case_profile)) if case_profile else None
    if context:
        # Use the same validation/composition as the investigator; no private inputs.
        with_questions(context, public)
    sources = [Path(p) for p in images]
    if not sources or any(not p.is_file() for p in sources):
        raise ValueError("supply the complete set of evidence image files")
    if len({p.name for p in sources}) != len(sources):
        raise ValueError("image basenames must be unique")
    # Only explicit image inputs are hashed. No repository scan or private reference read.
    evidence = [{"name": p.name, "bytes": p.stat().st_size, "sha256": digest(p)} for p in sources]
    destination = Path(out)
    destination.mkdir(parents=True, exist_ok=False)

    def write(name, value):
        (destination / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")

    write("questions.json", public)
    if context:
        write("case-profile.json", context.public_dict())
    write("answers.template.json", {"schema_version": 2, "case_id": public["case_id"],
                                    "answers": [{"question_id": q["id"], "status": "unknown"}
                                                for q in public["questions"]]})
    prompt = ["# Investigation instructions", "", public.get("title", public["case_id"]), "",
              "Use only the supplied images, public case context, and public question contract.",
              "Answer every question. Give complete requested lists and attributes.",
              "Use unknown when the evidence does not support an answer.",
              "Keep evidence citations in the investigation report.",
              "Include exactly one JSON code block with the complete schema_version 2 submission.",
              "Use the case_id and question_id values in the contract.",
              "The JSON block must contain answers, not a self-assessed score.", ""]
    if context:
        prompt += ["## Public case context", "", context.name, "", context.brief, "",
                   "The same case-profile.json and questions.json are supplied to both systems.", ""]
        if context.time_zone:
            prompt += ["Declared case timezone: " + context.time_zone, ""]
    prompt += ["## Public contract", "", "```json", json.dumps(public, indent=2, ensure_ascii=False), "```", ""]
    (destination / "MULDER.md").write_text("\n".join(prompt))
    manifest = {"schema_version": 1, "status": "prepared_not_finalized_not_run",
                "case_id": public["case_id"], "question_count": len(public["questions"]),
                "evidence": evidence, "evidence_copied": False,
                "inputs": {name: digest(destination / name) for name in
                           ["questions.json", "answers.template.json", "MULDER.md"]
                           + (["case-profile.json"] if context else [])},
                "comparison": {"trials_per_system": 3, "model_id": None,
                               "model_provider": None, "budget_per_trial": None,
                               "mulder_version": None, "mulder_image_digest": None,
                               "chain_of_proof_commit": None, "reference_sha256": None},
                "before_execution": [
                    "Finalize and independently review the full answer contract.",
                    "Resolve list scope and all draft unevaluable questions.",
                    "Review acquisition metadata: no key-derived serial mapping exclusive to one system.",
                    "Freeze both system versions, model, budgets, evidence and private reference hashes.",
                    "Confirm Mulder emits the requested typed submission without changing its substance.",
                    "Receive the user's instruction to run after finalization."],
                "private_reference_included": False, "model_invoked": False}
    write("manifest.json", manifest)
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", required=True)
    parser.add_argument("--case-profile", help="reviewed public case context, identical for both systems")
    parser.add_argument("--images", nargs="+", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    manifest = prepare(args.questions, args.images, args.out, args.case_profile)
    print(f"Prepared {manifest['question_count']} questions and {len(manifest['evidence'])} image hashes. No investigation started.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
