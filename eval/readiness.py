"""Public-only contract and evidence readiness, never an accuracy score.

Use this before a new dataset run. It identifies unsupported answer meanings and
catalog roles with no observed values. It cannot determine which evidence answers
a question or certify completeness, and it never reads a private reference.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from agent.answer_projection import catalog
from agent.answer_requirements import inspect
from agent.case import read_question_profile
from checker.catalog import ROLES
from checker.facts import open_source


def assess(public, source):
    kinds = Counter(fact.kind for fact in source.all())
    fields = catalog()["forms"]
    by_type = {role.semantic_type: role for role in ROLES.values()}
    questions = []
    for question in public["questions"]:
        requirements = inspect(question["answer_schema"], fields)["requirements"]
        for requirement in requirements:
            types = requirement.get("requirement", {}).get("semantic_types", [])
            observations = {name: kinds[by_type[name].kind] for name in types if name in by_type}
            if observations:
                requirement["role_observation_counts"] = observations
                requirement["evidence_note"] = (
                    "Counts are role rows only. They do not prove a complete linked triple, relevance, or the answer.")
        questions.append({"question_id": question["id"], "requirements": requirements,
                          "unannotated": not requirements,
                          "unsupported_fields": sum(row["status"] == "no_catalog_support" for row in requirements),
                          "invalid_fields": sum(row["status"] == "invalid" for row in requirements)})
    return {"schema_version": 1, "case_id": public["case_id"], "questions": questions,
            "question_count": len(questions), "fact_count": sum(kinds.values()),
            "facts_by_kind": dict(kinds),
            "unsupported_field_count": sum(row["unsupported_fields"] for row in questions),
            "invalid_field_count": sum(row["invalid_fields"] for row in questions),
            "unannotated_question_count": sum(row["unannotated"] for row in questions),
            "scope": "Public contract support and observed role counts only; not answer accuracy, completeness, or a Lean certificate."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--facts", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    public = read_question_profile(args.questions)
    result = assess(public, open_source(args.facts))
    with args.out.open("x") as output:
        json.dump(result, output, indent=2)
        output.write("\n")
    print(json.dumps({key: value for key, value in result.items() if key not in ("questions", "facts_by_kind")}))
    return int(result["invalid_field_count"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
