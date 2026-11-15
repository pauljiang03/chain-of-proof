"""Deterministic, non-certifying explanations of rejected proof obligations.

This module never invokes Lean, changes records, or decides acceptance. It describes
failed bricks already returned by the checker and resolves their values from the same
cited source. Unknown diagnostic formats remain unclassified rather than guessed.
"""
from __future__ import annotations

import re

from . import claims

DISCLAIMER = (
    "Diagnostic only: this is not a certificate, and refusal alone does not prove a claim false. "
    "Suggested evidence may not exist. Additional records do not by themselves prove intent or causation."
)


def _gap(requirements, summary=None):
    return {"status": "diagnostic",
            "summary": summary or f"The whole claim remains unproved; {len(requirements)} unmet condition(s) are described.",
            "requirements": requirements, "disclaimer": DISCLAIMER}


def _need(category, reason, action, fact_ids=(), observed=None, required=None):
    result = {"category": category, "reason": reason, "action": action,
              "fact_ids": list(dict.fromkeys(fact_ids))}
    if observed is not None:
        result["observed"] = observed
    if required is not None:
        result["required"] = required
    return result


def malformed(reason):
    """Shared entry point for syntax errors caught before checker.check is called."""
    return _gap([_need("malformed_claim", str(reason),
        "Correct the JSON/argument structure using the published claim schema. "
        "Fixing syntax supplies no evidence and does not establish the claim.")])


def execution(reason):
    """Fallback when an execution/diagnostic failure has no classified obligation."""
    return _gap([_unclassified(str(reason))])


def _unsupported(raw):
    pending = [raw]
    while pending:
        node = pending.pop()
        if not isinstance(node, dict) or len(node) != 1:
            continue
        name, args = next(iter(node.items()))
        if name == "both" and isinstance(args, list):
            pending.extend(reversed(args))
        elif name not in claims.SETS and name != "both":
            return name
    return None


def _required(part, relation, **values):
    return {"claim_part": claims.to_json(part), "rules": claims.rules(part),
            "relation": relation, **values}


def _record(fact, source):
    return {"id": fact.id, "kind": fact.kind,
            "obj": {"id": fact.obj, "text": source.string(fact.obj)},
            "aux": {"id": fact.aux, "text": source.string(fact.aux)},
            "t_us": fact.t, "uncertainty_us": fact.res,
            "time_meaning": fact.prov.get("time_meaning", "not specified in provenance")}


def _unclassified(reason, part=None, fact_ids=()):
    return _need("execution_or_unclassified", reason,
        "Inspect the checker diagnostics and source binding before retrying. "
        "Do not treat an execution limit or unclassified failure as missing evidence or a false claim.",
        fact_ids, required=_required(part, "successful evaluation of the stated obligations") if part else None)


def _brick_failure(brick, part, facts, source):
    """Recognize only the current Lean primitive diagnostics; no inferred rules."""
    match = re.fullmatch(r"FAIL is (\d+) \(?([A-Za-z][A-Za-z0-9]*)\)?", brick)
    if match:
        fid, expected = int(match[1]), match[2]
        fact = facts.get(fid)
        if fact is None or fact.kind == expected:
            return _unclassified("Failed kind diagnostic does not agree with the available cited row.", part, [fid])
        return _need("wrong_record_type",
            f"Record {fid} has kind {fact.kind}; this part requires {expected}.",
            "Retrieve an independently sourced record of the required type, if available, or state only "
            "what the current artifact supports through a reviewed form. Do not relabel the existing record.",
            [fid], _record(fact, source), _required(part, "record kind must match", kind=expected))

    match = re.fullmatch(r"FAIL link (\d+) \(?(obj|aux)\)? (\d+) \(?(obj|aux)\)?", brick)
    if match:
        left_id, left_slot, right_id, right_slot = int(match[1]), match[2], int(match[3]), match[4]
        left, right = facts.get(left_id), facts.get(right_id)
        if left is None or right is None or getattr(left, left_slot) == getattr(right, right_slot):
            return _unclassified("Failed identity diagnostic does not agree with the available cited rows.", part,
                                 [left_id, right_id])
        return _need("contradictory_identity_or_value",
            f"The existing rows conflict with the requested equality: record {left_id}.{left_slot} "
            f"and record {right_id}.{right_slot} identify different encoded values.",
            "Review the cited artifacts and intended relationship. A different linkage requires independent "
            "source evidence connecting the intended entities. Preserve the conflicting serials, paths or "
            "other values; do not rewrite them to make this claim pass.",
            [left_id, right_id], {"records": [_record(left, source), _record(right, source)]},
            _required(part, "exact encoded identity equality", left={"fact_id": left_id, "slot": left_slot},
                      right={"fact_id": right_id, "slot": right_slot}))

    match = re.fullmatch(r"FAIL val (\d+) \(?(obj|aux)\)? (\d+)", brick)
    if match:
        fid, slot, expected = int(match[1]), match[2], int(match[3])
        fact = facts.get(fid)
        if fact is None or getattr(fact, slot) == expected:
            return _unclassified("Failed value diagnostic does not agree with the available cited row.", part, [fid])
        return _need("contradictory_identity_or_value",
            f"Record {fid}.{slot} conflicts with the requested encoded value {expected}.",
            "Review the source and the asserted value. Preserve the recorded value; a different assertion "
            "requires its own source support, not editing the evidence to meet the requested constant.",
            [fid], _record(fact, source),
            _required(part, "encoded value equality", slot=slot, value_id=expected,
                      value_text=source.string(expected)))

    match = re.fullmatch(r"FAIL before (\d+) (\d+)", brick)
    if match:
        left_id, right_id = int(match[1]), int(match[2])
        left, right = facts.get(left_id), facts.get(right_id)
        if left is None or right is None or left.t + left.res + right.res < right.t:
            return _unclassified("Failed time diagnostic does not agree with the available cited rows.", part,
                                 [left_id, right_id])
        if left_id == right_id:
            state, reason = "same_record", "The claim requires a record to strictly precede itself."
            action = ("Identify the distinct observations the claim concerns, if any. More precision cannot "
                      "make this same record precede itself; do not manufacture another record ID.")
        elif right.t + right.res + left.res < left.t:
            state = "reverse_order_conflict"
            reason = "The cited timestamp intervals establish the reverse of the requested order."
            action = ("Review the proposed event order and artifact time meanings. Preserve the recorded "
                      "times; additional precision alone cannot reverse these separated intervals. Any "
                      "different timeline requires independent source support.")
        else:
            state = "overlapping_or_insufficiently_separated"
            reason = ("The recorded times do not establish the requested order beyond their combined uncertainty."
                      + (" Their central timestamps are reversed." if left.t > right.t else ""))
            action = ("Seek an independent, more precise timestamp record for the same observations, if available, "
                      "with documented clock/time semantics. Keep the existing uncertainty; do not narrow it "
                      "without evidence. Otherwise leave the ordering unresolved.")
        return _need("uncertain_or_wrong_time_order", reason, action, [left_id, right_id],
            {"order_status": state, "records": [_record(left, source), _record(right, source)],
             "gap_us": right.t - left.t, "combined_uncertainty_us": left.res + right.res},
            _required(part, "left.t_us + left.uncertainty_us + right.uncertainty_us < right.t_us",
                      earlier_fact_id=left_id, later_fact_id=right_id))
    return _unclassified("The checker returned an unrecognized failed obligation: " + brick,
                         part, claims.fact_ids(part))


def diagnose(raw_claim, source, *, parsed=None, facts=None, parts=None, reason=""):
    """Explain a rejection without running the kernel or revising its decision."""
    if parsed is None:
        try:
            parsed = claims.parse(raw_claim)
        except claims.ClaimError as error:
            unknown = _unsupported(raw_claim)
            if unknown is not None:
                return _gap([_need("unsupported_rule_or_form",
                    f"There is no approved formal rule for claim form {unknown!r}.",
                    "Specify, test and review a formal rule and an evidence reader for the facts it needs, "
                    "or leave the statement explicitly unproved. More unrelated records cannot establish "
                    "an unsupported inference.", observed={"form": unknown},
                    required={"reviewed_rule_and_source_semantics": True})])
            return malformed(reason or str(error))
    bound_facts_available = facts is not None
    cited = claims.fact_ids(parsed)
    facts = facts if facts is not None else source.get(cited)
    missing = set(cited) - facts.keys()
    if missing:
        requirements = []
        for part in claims.parts(parsed):
            ids = claims.fact_ids(part)
            absent = [fid for fid in ids if fid in missing]
            if absent:
                requirements.append(_need("missing_record",
                    f"These proposed record IDs do not resolve in the current evidence snapshot: {absent}.",
                    "Re-query this snapshot and retrieve the actual source-bound records for the intended "
                    "claim. If the needed artifact has not been extracted, a reviewed reader and a new "
                    "snapshot may be needed. Do not invent IDs or reuse IDs from a different snapshot.",
                    absent, {"missing_fact_ids": absent, "present_fact_ids": [i for i in ids if i in facts]},
                    _required(part, "every cited ID resolves to the intended source-bound record")))
        return _gap(requirements)
    if claims.census_of(parsed):
        if parsed[0] == "filesystemSetDeleted":
            actual = (claims.filesystem_set_actual(parsed, facts) if bound_facts_available else
                      {"membership_binding": "unavailable", "reason": reason})
            capacity = "can cover at most" in reason
            unknown = actual.get("unknown_flag_ids", [])
            category = ("execution_or_unclassified" if capacity or "kernel" in reason else
                        "missing_record" if unknown or actual.get("declaration_valid") is False else
                        "contradictory_identity_or_value")
            return _gap([_need(category,
                reason if capacity else "The proposed count and deletion aggregate are not established for the exact declared extracted set.",
                "Inspect the declared extraction scope, every scoped membership record and each actual filesystem allocation flag. "
                "Missing or unreadable flags require the corresponding source record or a reviewed reader; missing declarations "
                "require a completed recorded enumeration. Preserve contradictory flags and duplicate identities. Do not remove "
                "members or substitute a different set to obtain the proposed result. This establishes neither recoverability nor secure erasure.",
                sorted(facts), actual,
                _required(parsed, "one declaration, exact nonempty unique membership, all flags known, exact count and aggregate",
                          count=parsed[1][1], all_deleted=parsed[1][2], maximum_members=claims.MAX_FILESYSTEM_SET))])
        if "a census can cover at most" in reason:
            return _gap([_need("execution_or_unclassified",
                reason + "; this is a checker capacity limit, not an evidence-absence claim.",
                "Use a record-query summary clearly labeled outside the proof, or review an implementation "
                "that can check the full census scope. Do not present a partial table as a complete census.",
                required=_required(parsed, "check every extracted record in the declared census scope",
                                   current_limit=claims.MAX_CENSUS))])
        if parts:
            actual, expected = claims.census_actual(parsed, facts), parsed[1][-1]
            if actual != expected:
                return _gap([_need("contradictory_identity_or_value",
                    f"The proposed census is {expected}, but this extracted-record scope contains {actual}.",
                    "Review the stated census scope and source snapshot. This is a count of extracted records, "
                    "not all real-world events. Preserve the snapshot rather than adding/removing rows to "
                    "satisfy the proposed count.", sorted(facts),
                    {"count": actual, "scope": "current extracted records"},
                    _required(parsed, "exact count in the declared extracted-record scope", count=expected))])
    requirements = []
    for item in parts or []:
        if item.get("ok"):
            continue
        try:
            part = claims.parse(item["part"])
        except (KeyError, claims.ClaimError):
            requirements.append(_unclassified("A failed-part diagnostic could not be parsed."))
            continue
        failures = [line for line in item.get("bricks", []) if isinstance(line, str) and line.startswith("FAIL ")]
        requirements.extend(_brick_failure(line, part, facts, source) for line in failures)
        if not failures:
            requirements.append(_unclassified("This part failed without a classified failed-brick diagnostic.",
                                              part, claims.fact_ids(part)))
    return _gap(requirements or [_unclassified(reason or "The checker did not provide a classified failed obligation.",
                                               parsed, cited)])
