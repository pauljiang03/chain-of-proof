"""Read-only contract checks and synthetic matcher tests; never a system score."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from agent.case import read_question_profile
from eval.benchmark import score, validate_reference
from eval.key_audit import audit


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(source_root=ROOT):
    reference = json.loads((HERE / "reference.json").read_text())
    public = read_question_profile(HERE / "questions.json")
    validate_reference(reference)
    checks = ["private_reference_valid", "public_profile_valid"]
    assert reference["case_id"] == public["case_id"]
    assert len(reference["questions"]) == len(public["questions"]) == 1
    q, p = reference["questions"][0], public["questions"][0]
    assert q["id"] == p["id"] == "Q53"
    assert q["prompt"] == p["prompt"] and q["match"] == p["match"]
    assert q["evaluation"]["status"] == "scorable"
    assert set(q["expected"]) == {"files"}
    assert len(q["expected"]["files"]) == 17
    assert set(p["answer_schema"]["properties"]) == {"files"}
    assert p["answer_schema"]["additionalProperties"] is False
    checks.append("same_single_question_scope_and_match_rules")

    original_path = ROOT / reference["derived_from"]["reference_path"]
    original_public = ROOT / reference["derived_from"]["public_profile_path"]
    assert digest(original_path) == reference["derived_from"]["reference_sha256"]
    assert digest(original_public) == reference["derived_from"]["public_profile_sha256"]
    original = next(q for q in json.loads(original_path.read_text())["questions"] if q["id"] == "Q53")
    assert q["expected"]["files"] == original["expected"]["files"]
    assert reference["source_supplemental"]["optional_carving"] == original["expected"]["optional_carving"]
    checks.append("frozen_inputs_unchanged_and_all_metadata_rows_preserved")

    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                assert key not in {"expected", "field_sources", "source_supplemental", "source_document"}
                yield from walk(item)
        elif isinstance(value, list):
            for item in value:
                yield from walk(item)
        elif isinstance(value, str):
            yield value

    public_text = "\n".join(walk(public))
    for row in q["expected"]["files"]:
        for value in (row["path"], row["size_as_printed"], row["recovery_method"]):
            assert value not in public_text, "private expected value leaked into public profile"
    for forbidden in ("reference.json", "leakage-answers", "benchmark_nist.json"):
        assert forbidden not in public_text
    checks.append("no_private_fields_answer_paths_sizes_methods_or_key_locators_in_public_profile")

    bound_reference = deepcopy(reference)
    document = bound_reference["source_document"]
    document["pdf_path"] = str(Path(source_root) / document["pdf_path"])
    binding = audit(bound_reference, Path(source_root) / document["path"])
    assert binding["source_binding_passed"], binding
    checks.append("source_document_pdf_span_and_own_row_literal_bindings_pass")

    # Self-tests deliberately feed the copied key to the matcher. They test the
    # contract mechanism, not recovery, a model, or the truth of the source.
    submission = {"schema_version": 2, "case_id": reference["case_id"], "answers": [
        {"question_id": "Q53", "status": "answered", "answer": deepcopy(q["expected"])}]}
    baseline = score(reference, submission)
    assert baseline["perfect_submission"] and baseline["atomic"]["true_positive"] == 85
    appendix = deepcopy(submission)
    appendix["appendices"] = {"optional_carving": {"synthetic_test_only": "ignored"},
                             "display_observations": [{"synthetic_test_only": True}]}
    result = score(reference, appendix)
    for key in ("question_counts", "atomic", "questions", "perfect_submission"):
        assert result[key] == baseline[key]
    checks.append("top_level_optional_and_observation_appendices_do_not_change_score")
    for label in ("missing_field", "wrong_viewable", "extra_answer_field"):
        changed = deepcopy(submission)
        answer = changed["answers"][0]["answer"]
        if label == "missing_field":
            del answer["files"][0]["viewable"]
        elif label == "wrong_viewable":
            answer["files"][0]["viewable"] = False
        else:
            answer["optional_carving"] = {"synthetic_test_only": True}
        result = score(reference, changed)
        assert not result["perfect_submission"]
        assert result["atomic"]["missing" if label == "missing_field" else "wrong"] >= 1
        checks.append(label + "_does_not_receive_full_credit")
    return {"schema_version": 1, "validation_kind": "contract_validation_and_synthetic_self_tests",
            "case_id": reference["case_id"], "passed": True, "checks": checks,
            "reference_sha256": digest(HERE / "reference.json"),
            "public_profile_sha256": digest(HERE / "questions.json"),
            "source_binding": binding,
            "models_or_extraction_run": False,
            "system_accuracy_measured": False,
            "note": "Source binding and scorer behavior only; not proof of reference truth, independent semantic review, display observation, or Lean certification."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(validate(args.source_root), indent=2))
