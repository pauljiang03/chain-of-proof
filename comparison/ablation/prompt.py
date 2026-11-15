"""Matched public investigator prompts; no reference answers or evaluator imports."""
from __future__ import annotations

import json

from agent.brief import case_context, question_context, record_context

PROTOCOLS = ("literal-v1", "claim-bindings-v2", "claim-bindings-v3")

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


COMMON_BINDINGS = """YOUR SHARED TOOLS
forms: approved claim forms and the public catalog of semantic fields for answer bindings.
sql(query): one read-only SELECT over extracted facts; rows and string cells are bounded.
fact(id): the full source-bound record, including unclipped values and provenance.
check(question, claim, revises?): submit a JSON object claim; optional revisions name a
prior proposal. claims may instead be a nonempty ordered batch of JSON objects.
plan: public question work, unresolved notes and neutral coverage/inventory diagnostics.
update_question(question_id, searched?, unresolved?, next_actions?, status?): record work
notes. It cannot attach certified finding IDs or assert that a question is proved complete.
inventory_page(question_id, kinds?, exhibits?, page_size?, cursor?): exact kind/exhibit
filters in record-ID order, with bounded pages and saved continuation cursors.
There is no product answer, conclude, collect, reference, scorer or projection tool.

Use these tools only through the supplied bridge. The terminal is transport, not an
alternate evidence reader. Do not execute arbitrary commands, inspect other files,
read private references or prior runs, browse the network, or contact other agents.
These are procedural restrictions, not an operating-system sandbox.

HOW TO WORK
Start with plan and forms. Explore with sql, and inspect full records with fact. Link
each proposed answer field to a semantic field of a specific submitted claim using the
forms catalog. Use only public questions and supplied evidence, never expected answers.
For inventories, continue inventory_page with its next_cursor and exactly the same
question_id, filters and page_size. Returned rows and exhaustion describe that predicate
in this extracted snapshot; they do not establish inspection or forensic completeness.
Fetch fact(id) before using clipped values. Preserve artifact-specific timestamp meanings,
scope and source distinctions. Apply the public question's filters instead of dumping
unrelated rows. A count certificate alone does not reproduce an inventory's values.

Keep supported partial fields even when another requested field is unknown. Record
missing fields and concrete next searches with update_question. A checker capacity
refusal does not erase observed records; keep its limitation explicit. Do not guess
intent, causation, physical-device identity or dates, equate a shared volume label with
physical identity, or treat optical settings/locks as a completed physical-disc write.

Before finishing, call plan again. Use remaining time for feasible unresolved fields,
unfinished pages, and known claim fields not yet bound to the requested answer. Record
why work remains blocked. Reviewed work notes and coverage diagnostics are not proof
of answer accuracy or completeness. Respect the controller's fixed time cap.

FINAL RESPONSE: EXPLICIT BINDINGS
Write a concise evidence summary and exactly one fenced json block in this shape:
{"schema_version":1,"case_id":"<public case_id>","bindings":[],"unanswered":[]}
Each binding names candidate_id (use the finding_id returned by C), question_id, path,
part and field; format is optional and must be listed in the forms catalog. path is an
array of object keys and zero-based array indices. part is the zero-based index in the
flattened claim parts. The whole submitted claim remains one filtering dependency.
For example, a supported device_serial field might bind to ["devices",0,"serial"].
Use exact returned candidate IDs and catalog fields. Never invent a binding from an
expected answer. claim_sha256 may be omitted: after the run, the coordinator fills only
that missing metadata from the exact named saved claim. A supplied hash is never fixed.
Optional literal value assertions, when supplied, are preserved and never repaired.

Account for every public question through at least one binding or one unanswered item
{"question_id":"<id>","reason":"<specific remaining gap>"}. Do not use both for the
same question. For a partial question, bind its known fields and describe the unresolved
fields in work notes and your summary. Do not turn them into guessed or null values.
An unanswered item is for a question with no submitted answer-field binding. Unsupported
bindings and conflicts remain explicit; no prose-to-answer conversion or answer repair
will occur. The same frozen field projector is used for A and C. B later filters whole
A candidates without changing their projected values or un-hiding prior conflicts.
Claim acceptance and answer correctness are separate measurements.
"""


def build_prompt(profile, public_questions: dict, arm: str, protocol="literal-v1") -> str:
    if arm not in GATE:
        raise ValueError("arm must be A or C")
    if protocol not in PROTOCOLS:
        raise ValueError("unsupported ablation protocol")
    if protocol != "literal-v1":
        example = {"schema_version": 1, "case_id": public_questions["case_id"],
                   "bindings": [], "unanswered": [
                       {"question_id": q["id"], "reason": "Replace with the actual gap, or remove when binding known fields."}
                       for q in public_questions["questions"]]}
        return (case_context(profile) + record_context(profile) + question_context(profile)
                + GATE[arm] + "\n" + COMMON_BINDINGS
                + ("\nDURABLE V3: checkpoint(document) saves a full binding document atomically. Call it early and repeatedly before the fixed deadline, accounting for every question through bindings or unanswered. Invalid updates preserve the last checkpoint. preview(document) returns bounded uncertified public claim-field/schema diagnostics identically in A and C, without proof checking. Only the last valid in-budget checkpoint supplies answers, including on timeout; final prose/JSON cannot replace it. Missing checkpoints leave answers unavailable. Strict public claim requirements apply to every binding.\n" if protocol == "claim-bindings-v3" else "")
                + "\nSubmission structure (account for every question):\n"
                + json.dumps(example, ensure_ascii=False, indent=2) + "\n")
    example = {"schema_version": 2, "case_id": public_questions["case_id"],
               "answers": [{"question_id": q["id"], "status": "unknown"}
                           for q in public_questions["questions"]]}
    return (case_context(profile) + record_context(profile) + question_context(profile)
            + GATE[arm] + "\n" + COMMON + "\nSubmission shape (replace unknown where supported):\n"
            + json.dumps(example, ensure_ascii=False, indent=2) + "\n")
