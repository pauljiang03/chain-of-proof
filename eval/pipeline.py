"""One explicit evaluation path: fresh certified run -> answers -> neutral benchmark.

This module does not choose an answer key, dataset adapter or case implicitly.
External structured answers can use the same benchmark without claiming Lean proof.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from agent.case import NIST_CASE_ID, read_question_profile
from checker.facts import open_source
from verifier.verify import verify_run
from . import benchmark


@dataclass
class Plan:
    case_id: str | None = None
    reference: dict | None = None
    questions: dict | None = None
    adapter: str | None = None
    answers: dict | None = None
    inputs: dict | None = None
    reason: str | None = None

    @property
    def measured(self):
        return self.reason is None and self.reference is not None


def _load(path):
    path = Path(path)
    return json.loads(path.read_text()), {"path": str(path),
                                         "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def prepare(reference=None, questions=None, adapter=None, answers=None, case_id=None,
            disabled=False):
    if adapter and answers:
        raise ValueError("choose --adapter or --answers, not both")
    public = read_question_profile(questions) if questions else None
    if public and case_id and public["case_id"] != case_id:
        raise ValueError("public questions case_id does not match the selected case")
    selected_case = public["case_id"] if public else case_id
    if disabled:
        return Plan(selected_case, questions=public, reason="--no-score")
    if not reference:
        if adapter or answers:
            raise ValueError("--adapter/--answers requires an explicit --reference and --questions")
        return Plan(selected_case, questions=public, reason="No explicit --reference supplied")
    if public is None:
        raise ValueError("--reference requires an explicit public --questions profile")
    key, key_input = _load(reference)
    benchmark.validate_reference(key)
    if key["case_id"] != selected_case:
        raise ValueError("reference case_id does not match public questions")
    if {q["id"] for q in key["questions"]} != {q["id"] for q in public["questions"]}:
        raise ValueError("reference and public profile must declare the same question IDs")
    public_prompts = {q["id"]: q["prompt"].strip() for q in public["questions"]}
    if any(q["prompt"].strip() != public_prompts[q["id"]] for q in key["questions"]):
        raise ValueError("reference and public profile question prompts differ")
    if adapter and (adapter != "nist" or selected_case != NIST_CASE_ID):
        raise ValueError("the nist adapter is only available for the declared NIST case; "
                         "other cases need compatible structured --answers")
    inputs = {"reference": key_input, "public_questions": _load(questions)[1]}
    submission = None
    if answers:
        submission, inputs["answers"] = _load(answers)
        # Validate a supplied submission before starting any expensive run.
        benchmark.score(key, submission)
    reason = None if adapter or answers else "No compatible --adapter or structured --answers supplied"
    return Plan(selected_case, key, public, adapter, submission, inputs, reason)


def _write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def evaluate(plan, trusted_run, answers_output, results_output, gate_result=None,
             *, facts_path=None, verification_output=None):
    """Reverify the bundle before adapting, then score its structured answers."""
    if not isinstance(trusted_run, dict) or not isinstance(trusted_run.get("case", {}), dict):
        raise ValueError("run must be an object with object-valued case metadata")
    run_case = trusted_run.get("case", {}).get("case_id")
    if run_case and plan.case_id and run_case != plan.case_id:
        raise ValueError("run case_id does not match the evaluation case")
    paths = [answers_output, results_output]
    if verification_output is not None:
        paths.append(verification_output)
    if len({Path(p).resolve() for p in paths}) != len(paths):
        raise ValueError("evaluation output paths must be distinct")
    for path in paths:
        if Path(path).exists() or Path(path).is_symlink():
            raise ValueError(f"refusing to overwrite existing evaluation output: {path}")
    if not plan.measured:
        result = {"schema_version": 2, "case_id": plan.case_id,
                  "evaluation": {"measured": False, "reason": plan.reason}}
    else:
        if plan.adapter == "nist":
            if facts_path is None or verification_output is None:
                raise ValueError("adapter evaluation requires --facts and a new verification output")
            source = open_source(facts_path)
            verification = verify_run(trusted_run, source)
            verification.update(facts=str(facts_path),
                                facts_sha256=hashlib.sha256(Path(facts_path).read_bytes()).hexdigest())
            _write_new(verification_output, verification)
            if not verification["passed"]:
                raise ValueError("certificate verification failed; no answers or score produced")
            from .nist_answers import generate
            submission = generate(trusted_run, plan.questions)
            origin = "Explicit NIST adapter over independently reverified certificates"
        else:
            submission = plan.answers
            origin = "Explicit external structured answers; no Lean certification implied"
        result = benchmark.score(plan.reference, submission)
        result["evaluation"] = {"measured": True, "answer_origin": origin,
                                "adapter": plan.adapter}
        result["inputs"] = plan.inputs
        _write_new(answers_output, submission)
    result["gate_regression"] = gate_result or {"measured": False,
                                               "reason": "No explicit gate fixture supplied"}
    _write_new(results_output, result)
    print(benchmark.report(result) if plan.measured else "not measured: " + plan.reason)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Independently verify an existing run, adapt its answers, and score them without a model.")
    parser.add_argument("--run", required=True, help="existing certified run bundle")
    parser.add_argument("--facts", required=True, help="source facts bound by the certificates")
    parser.add_argument("--questions", required=True, help="public schema-v2 question contract")
    parser.add_argument("--reference", required=True, help="private schema-v2 scoring reference")
    parser.add_argument("--adapter", choices=("nist",), required=True)
    parser.add_argument("--out", required=True, help="new directory for answers/results/verification.json")
    args = parser.parse_args(argv)
    output = Path(args.out)
    try:
        if output.exists() or output.is_symlink():
            raise ValueError(f"refusing to overwrite existing evaluation directory: {output}")
        run, run_input = _load(args.run)
        if not isinstance(run, dict) or not isinstance(run.get("case", {}), dict):
            raise ValueError("run must be an object with object-valued case metadata")
        if not Path(args.facts).is_file():
            raise ValueError(f"facts input does not exist: {args.facts}")
        case_id = run.get("case", {}).get("case_id") or run.get("case_id")
        plan = prepare(args.reference, args.questions, args.adapter, case_id=case_id)
        plan.inputs["run"] = run_input
        output.mkdir(parents=True, exist_ok=False)
        evaluate(plan, run, output / "answers.json", output / "results.json",
                 facts_path=args.facts, verification_output=output / "verification.json")
    except (ValueError, OSError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
