"""Matched public investigator prompts; no reference answers or evaluator imports."""
from __future__ import annotations

import json

from agent.brief import case_context, question_context, record_context


GATE = {
    "A": """SUBMISSION BEHAVIOR
check records each submitted claim and returns only its candidate ID and an unverified
receipt. It does not check meaning, evidence support, or correctness. No receipt is a
verified finding. Duplicate submissions remain separate candidates.
""",
    "C": """SUBMISSION BEHAVIOR
check invokes the existing proof checker and returns its verdict and diagnostics.
Accepted claims are certified within the approved forms; refusals explain what failed.
Read the feedback and correct or drop unsupported claims. Unchanged duplicate claims
return the earlier proposal. A refusal is not itself a ground-truth error label.
""",
}

COMMON = """YOUR FOUR TOOLS
forms: the available claim forms and their arguments.
sql(query): one read-only SELECT over the facts table.
fact(id): one full record with its provenance and entity IDs.
check(question, claim, revises?): submit a JSON object claim; optionally name an earlier
proposal with a string revises ID. A request may instead contain claims, a nonempty
ordered list of JSON objects. Question is a string. Contents of claim objects are
interpreted only according to the stated submission behavior.
There is no conclude tool.

Use only these tools through the supplied local bridge. The terminal is transport for
that bridge only: do not execute other commands, inspect files directly, access the
network, read reference answers, inspect another run, or invoke other agents/tools.
These are procedural experiment restrictions, not an operating-system sandbox.

HOW TO WORK
Start with forms, then explore with sql. Address every public question, its complete
scope, list members, source distinctions and requested attributes. Use fact to inspect
full records and their provenance. Do not omit supported answers to shorten a list.
Submit specific claims for the evidence your answers depend on. Use both to join up
to 64 parts, before for time-order claims, and exactly forms for record counts. When
correcting a prior proposal, name its ID with revises; do not invent revision links.
Preserve contradictions and timestamp uncertainty. If records or forms are missing,
identify the unanswered fields. Do not guess intent, causation, physical-device links,
or dates. A shared volume label is not a physical-device identity. Optical-disc locks,
temporary files and settings changes do not establish a completed write or its window.

FINAL RESPONSE
Give a concise evidence summary, with proposal/candidate IDs and unresolved limits.
Then include exactly one fenced json block containing a schema_version 2 submission.
Include every public question ID exactly once. For each item use question_id and
status (answered or unknown); an answered item must contain its literal answer matching
the public answer_schema. An unknown item may include reason. Do not self-grade or
replace uncertain values with guesses. These direct answers are unverified model
answers in both arms; certification of a claim does not certify the whole answer.
"""


def build_prompt(profile, public_questions: dict, arm: str) -> str:
    if arm not in GATE:
        raise ValueError("arm must be A or C")
    example = {"schema_version": 2, "case_id": public_questions["case_id"],
               "answers": [{"question_id": q["id"], "status": "unknown"}
                           for q in public_questions["questions"]]}
    return (case_context(profile) + record_context(profile) + question_context(profile)
            + GATE[arm] + "\n" + COMMON + "\nSubmission shape (replace unknown where supported):\n"
            + json.dumps(example, ensure_ascii=False, indent=2) + "\n")
