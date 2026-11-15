"""The written report of a run: what an investigator is handed.

    python3 -m checker.report runs/current/run.json > report.md

Certified findings by default; an explicitly requested appendix stays separate:

  Findings      sentences the proof checker generated and certified from records, with
                their strength, rules and the artifacts they cite.
  Appendix      optional investigator inferences. Not checked. Each names the certified
                findings it rests on; those citations do not certify the inference.

Nothing is reworded: every finding is the certificate's sentence as written.
"""
from __future__ import annotations

import json
import argparse
import sys
from collections import OrderedDict
from pathlib import Path

from . import citations


def _object(value):
    return value if isinstance(value, dict) else {}


def _supplied(mapping, key, absent="unavailable"):
    value = mapping.get(key)
    if value is None:
        return absent
    if isinstance(value, (dict, list)):
        value = json.dumps(value, sort_keys=True, ensure_ascii=False)
    return citations.text(value)


def _metric(section, field, *, known_total=False):
    section = _object(section)
    if section.get("status") == "invalid":
        return "invalid"
    if section.get("status") != "measured" and not known_total:
        return "unmeasured"
    return _supplied(section, field, "unmeasured")


def _problems(label, section):
    return [f"- {label}: {citations.text(problem)}" for problem in section.get("problems", []) or []]


def _audit_summary(run):
    if "audit" not in run:
        return []
    audit = _object(run["audit"])
    lines = ["## Audit integrity", ""]
    if audit.get("status") == "invalid" or audit.get("passed") is False:
        lines += ["**INVALID AUDIT — recorded events are diagnostic only.**", ""]
    elif audit.get("status") == "valid" and audit.get("passed") is True:
        lines += ["The bundle reports a passed audit integrity check. This renderer does not recheck the log.", ""]
    else:
        lines += ["Audit integrity is unavailable or not established by this bundle.", ""]
    lines += [f"- Declared status: {_supplied(audit, 'status')}; passed: {_supplied(audit, 'passed')}",
              f"- Recorded events: {_supplied(audit, 'count', 'unmeasured')}",
              f"- Audit file (literal path): {_supplied(audit, 'path')}",
              f"- File SHA-256: {_supplied(audit, 'sha256')}",
              f"- Chain head: {_supplied(audit, 'head')}",
              f"- Expected head supplied to audit check: {_supplied(audit, 'expected_head', 'not supplied')}"]
    if audit.get("scope"):
        lines.append("- Recorded scope: " + citations.text(audit["scope"]))
    lines += _problems("Audit problem", audit)
    lines += ["", "Inspect the separately supplied audit file to review its entries. Integrity does not "
              "establish authorship or complete history; detecting a complete rewrite requires an "
              "independently retained checkpoint. No audit-file link is inferred.", ""]
    return lines


def _coverage_summary(run):
    if "coverage" not in run:
        return []
    coverage = _object(run["coverage"])
    if coverage.get("schema_version") != 1:
        return ["## Recorded coverage", "", "Coverage summary is unavailable or has an unsupported schema.", ""]
    lines = ["## Recorded coverage", "",
             "These counts describe supplied records and logged activity. They do not establish "
             "investigation completeness. Answer presence is not answer accuracy. Unmeasured is not zero.", "",
             "| Recorded measure | Count | Status |", "| --- | ---: | --- |"]
    for key, field, label in (("extraction", "record_count", "Extracted records"),
                              ("inspection", "record_count", "Records explicitly returned by the fact tool"),
                              ("citations", "record_count", "Distinct cited records"),
                              ("certification", "finding_count", "Findings recorded as accepted")):
        section = _object(coverage.get(key))
        lines.append(f"| {label} | {_metric(section, field)} | {_supplied(section, 'status', 'unmeasured')} |")
    lines += ["", "Inspection counts do not include SQL aggregates or establish that a model understood "
              "a record. Accepted counts use recorded checker status, not an independent replay.",
              "Inspection audit integrity: " + _supplied(_object(coverage.get("inspection")), "audit_integrity") + ".", ""]
    questions = _object(coverage.get("questions"))
    lines += [f"Public question answer presence ({_supplied(questions, 'status', 'unmeasured')}): "
              f"total {_metric(questions, 'total_count', known_total=True)}; "
              + "; ".join(f"{label} {_metric(questions, field)}" for field, label in
                          (("answered_count", "answered"), ("unknown_count", "unknown"),
                           ("unanswered_count", "unanswered"), ("missing_count", "missing response"))) + ".", ""]
    for field, label in (("unknown_ids", "Unknown questions"), ("unanswered_ids", "Unanswered questions"),
                         ("missing_ids", "Questions with no response"), ("unexpected_ids", "Unexpected response IDs")):
        if questions.get(field):
            lines.append(f"- {label}: {_supplied(questions, field)}")
    failures = _object(coverage.get("failures"))
    execution, tools, extraction = (_object(failures.get(key)) for key in ("run", "tools", "extraction"))
    lines += ["", f"Run status: {_supplied(execution, 'status', 'unmeasured')}; ended: {_supplied(execution, 'ended')}.",
              f"Tool outcomes ({_supplied(tools, 'status', 'unmeasured')}): errors {_metric(tools, 'error_count')}; "
              f"refused calls {_metric(tools, 'rejected_count')}.",
              f"Extraction issues ({_supplied(extraction, 'status', 'unmeasured')}): "
              + "; ".join(f"{label} {_metric(extraction, field)}" for field, label in
                          (("reader_failure_count", "reader failures"), ("unsupported_source_count", "unsupported sources"),
                           ("warning_count", "warnings"), ("unclassified_issue_count", "unclassified issues"))) + ".", ""]
    for issue in extraction.get("issues", []) or []:
        if isinstance(issue, dict):
            lines.append(f"- Extraction {_supplied(issue, 'category')}: {_supplied(issue, 'message')}")
    for error in tools.get("errors", []) or []:
        if isinstance(error, dict):
            lines.append(f"- Tool error at recorded sequence {_supplied(error, 'sequence')}: "
                         f"{_supplied(error, 'tool')} ({_supplied(error, 'error_type')}); call {_supplied(error, 'call_id')}.")
    for key in ("extraction", "inspection", "citations", "certification", "questions"):
        lines += _problems(f"{key} summary problem", _object(coverage.get(key)))
    for key, section in (("tool outcomes", tools), ("extraction issues", extraction)):
        lines += _problems(f"{key} summary problem", section)
    for limitation in coverage.get("limitations", []) or []:
        lines.append("- Limitation: " + citations.text(limitation))
    return lines + [""]


def _attempt_table(attempts):
    lines = ["| Recorded attempt | Finding | Outcome | Started / completed | Explicit revision |",
             "| --- | --- | --- | --- | --- |"]
    for raw in attempts:
        attempt = _object(raw)
        outcome = _supplied(attempt, "status", "unknown")
        if attempt.get("duplicate_of") is not None:
            outcome += " of " + _supplied(attempt, "duplicate_of") + " (no new proof)"
        revision = "none recorded"
        if attempt.get("revises") is not None or attempt.get("revision_status") not in (None, "none"):
            revision = (f"revises {_supplied(attempt, 'revises')}; "
                        f"status {_supplied(attempt, 'revision_status', 'unknown')}")
        if attempt.get("revision_error"):
            revision += ": " + citations.text(attempt["revision_error"])
        lines.append(f"| {_supplied(attempt, 'attempt_id')} | {_supplied(attempt, 'finding_id')} | {outcome} | "
                     f"{_supplied(attempt, 'started_at')} / {_supplied(attempt, 'completed_at')} | {revision} |")
        if attempt.get("error"):
            lines.append(f"| Recorded error | | {citations.text(attempt['error'])} | | |")
        for problem in attempt.get("problems", []) or []:
            lines.append(f"| Attempt diagnostic | | {citations.text(problem)} | | |")
    return lines + [""]


def _history_summary(run):
    if "history" not in run:
        return []
    history = _object(run["history"])
    if history.get("schema_version") != 1:
        return ["## Recorded claim attempts", "", "Attempt history is unavailable or has an unsupported schema.", ""]
    lines = ["## Recorded claim attempts", "",
             "Recorded attempts only, not a complete history guarantee. Outcomes are recorded checker "
             "results, not independent verification. No revision or repair is inferred from similar claims.", ""]
    integrity = _object(history.get("audit_integrity"))
    if integrity.get("status") == "failed":
        lines += ["**INVALID HISTORY AUDIT — these events are diagnostic only.**", ""]
    elif integrity.get("status") in (None, "unavailable", "not_checked"):
        lines += [f"History audit integrity: {_supplied(integrity, 'status')}. "
                  "No integrity guarantee is supplied for these events.", ""]
    else:
        lines += [f"History audit integrity: {_supplied(integrity, 'status')}; integrity does not establish completeness.", ""]
    if history.get("available") is not True:
        lines += ["History is unavailable; this does not establish that no attempts occurred.", ""]
    counts = _object(history.get("counts"))
    lines += ["Recorded counts: " + "; ".join(f"{label} {_supplied(counts, key, 'unmeasured')}" for key, label in
              (("attempts", "attempts"), ("accepted", "accepted"), ("refused", "refused"),
               ("duplicate", "duplicate"), ("failed", "failed"), ("unknown", "unknown"),
               ("explicit_revisions", "explicit revisions"), ("invalid_revisions", "invalid revision links"))) + ".", "",
              f"Order supplied by the history summary: {_supplied(history, 'ordering')}. "
              "Audit order is completed-event order; proposal-only logs retain their recorded order. "
              "Missing timestamps are not reconstructed.", ""]
    if isinstance(history.get("attempts"), list) and history["attempts"]:
        lines += _attempt_table(history["attempts"])
    coverage = _object(history.get("coverage"))
    lines += [f"Unmatched proposal rows: {_supplied(coverage, 'unmatched_proposal_rows', 'unmeasured')}; "
              f"attempts without timestamps: {_supplied(coverage, 'attempts_without_timestamps', 'unmeasured')}; "
              f"interrupted calls: {_supplied(coverage, 'interrupted_calls', 'unmeasured')}.", ""]
    if isinstance(history.get("unmatched_proposals"), list) and history["unmatched_proposals"]:
        lines += ["### Proposals with unknown placement relative to audit events", "",
                  "These rows are separate from the attempt sequence and its counts.", ""]
        lines += _attempt_table(history["unmatched_proposals"])
    lines += _problems("History problem", history)
    if history.get("disclaimer"):
        lines += ["", citations.text(history["disclaimer"])]
    return lines + [""]


def _proof_gaps(run: dict) -> list:
    gaps = [(r, r.get("proof_gap")) for r in run.get("rejections", [])
            if isinstance(r.get("proof_gap"), dict) and r["proof_gap"].get("status") == "diagnostic"]
    if not gaps:
        return []
    lines = ["## Not established / further evidence needed", "",
             "These are diagnostics for refused proposals, not certified findings. "
             "Refusal does not establish that a proposed claim is false. Suggested evidence "
             "does not establish that the claim will become provable.", ""]
    for rejection, gap in gaps:
        lines += [f"- **{citations.value(rejection, 'finding_id')}** (diagnostic, not certified): "
                  f"{citations.value(gap, 'summary')}"]
        for requirement in gap.get("requirements") or []:
            if not isinstance(requirement, dict):
                continue
            lines += [f"  - **{citations.value(requirement, 'category')}**: {citations.value(requirement, 'reason')}",
                      f"    Further evidence or action: {citations.value(requirement, 'action')}."]
            for key, label in (("fact_ids", "Fact IDs"), ("observed", "Observed"), ("required", "Required condition")):
                if key in requirement:
                    lines.append(f"    {label}: {citations.text(json.dumps(requirement[key], sort_keys=True, ensure_ascii=False))}.")
        if gap.get("disclaimer"):
            lines.append("  " + citations.text(gap["disclaimer"]))
    return lines + [""]


def _workflow_summary(run, findings):
    lines, by_id, duplicates = [], {}, set()
    for number, finding in findings:
        fid = finding.get("finding_id")
        if not isinstance(fid, str):
            continue
        if fid in by_id:
            duplicates.add(fid)
        by_id[fid] = (number, finding)
    eligible = {fid: item for fid, item in by_id.items() if fid not in duplicates
                and isinstance(item[1].get("english"), str) and item[1]["english"]}
    rows = lambda value: value if isinstance(value, list) else []
    if "collection" in run:
        receipt = _object(run["collection"])
        lines += ["## New evidence available", ""]
        if receipt.get("status") in ("completed", "completed_with_limitations") and receipt.get("continuation_required") is True:
            lines += ["A separate evidence snapshot was collected. It is not incorporated into the current findings. "
                      "Continue in a new run, query the new records and issue new proofs; old fact IDs and certificates "
                      "cannot be carried over as current proof.", ""]
            for key, label in (("status", "Collection status"), ("snapshot_id", "Snapshot ID"),
                               ("facts", "Facts path — literal text"), ("facts_sha256", "Facts SHA-256"),
                               ("config", "Intake configuration path — literal text"), ("health", "Extraction health path — literal text")):
                lines.append(f"- {label}: {_supplied(receipt, key)}")
            if receipt.get("note"):
                lines += ["", citations.text(receipt["note"])]
        else:
            lines += ["A completed collection requiring continuation is not established by this receipt. Supplied metadata:", "",
                      citations.fenced(citations.json_text(receipt), "json")]
        lines.append("")
    if "investigation" in run:
        plan = _object(run["investigation"])
        lines += ["## Investigation plan — agent-reported work", "",
                  "Work status, searches, unresolved questions and next actions are agent-reported notes, not proof. "
                  "Reviewed does not mean answered, accurate or complete.", ""]
        if plan.get("schema_version") != 1 or plan.get("status") == "unavailable":
            lines += ["A supported investigation plan is unavailable.", "", citations.fenced(citations.json_text(plan), "json"), ""]
        else:
            lines += [f"Plan revision: {_supplied(plan, 'revision')}; case ID: {_supplied(plan, 'case_id')}.", ""]
            for raw in rows(plan.get("questions")):
                question = _object(raw)
                lines += [f"### {_supplied(question, 'id')} — {_supplied(question, 'prompt')}", ""]
                for key, label in (("work_status", "Agent-reported work status"), ("finding_ids", "Stated finding IDs"),
                                   ("searched", "Reported searches"), ("unresolved", "Unresolved notes"),
                                   ("next_actions", "Proposed next actions")):
                    lines.append(f"- {label}: {_supplied(question, key)}")
                if "previous_run_notes" in question:
                    lines += ["", "Previous-run notes — unverified; no current proof is inferred:", "",
                              citations.fenced(citations.json_text(question["previous_run_notes"]), "json")]
                lines.append("")
            if plan.get("disclaimer"):
                lines += [citations.text(plan["disclaimer"]), ""]

    if "case_answers" in run:
        answers = _object(run["case_answers"])
        lines += ["## Question-by-question findings", "",
                  "Only exact sentences matching a unique current-run record marked verified are shown as certificate statements. "
                  "Question association does not prove relevance, accuracy or completeness. This renderer does not independently replay certificates.", ""]
        mismatch = (_object(run.get("case")).get("case_id") is not None and answers.get("case_id") is not None
                    and run["case"]["case_id"] != answers["case_id"])
        if (answers.get("schema_version") != 1 or answers.get("kind") != "certificate_sentence_answers"
                or answers.get("status") == "unavailable" or mismatch):
            lines += ["Question answers are unavailable, unsupported, or not bound to this case. Supplied content remains unverified:", "",
                      citations.fenced(citations.json_text(answers), "json"), ""]
        else:
            for raw in rows(answers.get("questions")):
                question = _object(raw)
                lines += [f"### {_supplied(question, 'id')} — {_supplied(question, 'prompt')}", "",
                          f"Declared answer presence: {_supplied(question, 'status')}; "
                          f"agent-reported work status: {_supplied(question, 'work_status')}.", ""]
                displayed = 0
                for raw_entry in rows(question.get("certified_findings")):
                    entry = _object(raw_entry)
                    linked = eligible.get(entry.get("finding_id")) if isinstance(entry.get("finding_id"), str) else None
                    if linked and entry.get("sentence") == linked[1]["english"]:
                        number, finding = linked
                        lines += [f"- **Recorded certificate statement {_supplied(finding, 'finding_id')}**: "
                                  f"{citations.text(finding['english'])} [Proof record](#proof-f{number}).",
                                  f"  Reported association: {_supplied(entry, 'association')}. "
                                  "This is not a proof that the question is answered."]
                        displayed += 1
                    else:
                        lines += ["An answer entry has no matching unique current-run certificate sentence. It is unverified:", "",
                                  citations.fenced(citations.json_text(raw_entry), "json"), ""]
                if not displayed:
                    lines += ["No bound certificate statement is available for this question. "
                              "This does not establish that no relevant evidence exists.", ""]
                for key, label in (("searched", "Reported searches — unverified"), ("unresolved", "Unresolved notes — unverified"),
                                   ("next_actions", "Proposed next actions — unverified")):
                    lines.append(f"- {label}: {_supplied(question, key)}")
                for key, label in (("refusals", "Refused proposals and diagnostics — not certified"),
                                   ("issues", "Question-association issues — not certified"),
                                   ("previous_run_notes", "Previous-run notes — unverified")):
                    if question.get(key):
                        lines += ["", label + ":", "", citations.fenced(citations.json_text(question[key]), "json")]
                lines.append("")
            if answers.get("disclaimer"):
                lines += [citations.text(answers["disclaimer"]), ""]

    if "conflicts" in run:
        review = _object(run["conflicts"])
        lines += ["## Cross-record review — unverified diagnostics", "",
                  "These are leads for review, not certified contradictions or a choice of which source is true. "
                  "Shared labels and repeated events can be legitimate. No diagnostic does not mean no conflict exists.", ""]
        if review.get("schema_version") == 1 and review.get("status") == "unavailable":
            lines += ["**Conflict review unavailable:** " + _supplied(review, "reason"), "",
                      "Recorded error type: " + _supplied(review, "error_type"), ""]
        elif review.get("schema_version") != 1 or review.get("status") != "diagnostic":
            lines += ["A supported diagnostic review is unavailable. Uninterpreted review metadata:", "",
                      citations.fenced(citations.json_text(review), "json"), ""]
        else:
            scope = _object(review.get("scope"))
            if scope.get("scan_truncated") is True or scope.get("diagnostics_truncated") is True:
                lines += ["**REVIEW TRUNCATED:** the scan or diagnostic output reached its limit. "
                          "Unshown records or diagnostics remain unreviewed here.", ""]
            for key, label in (("records_examined", "Records examined"), ("max_records", "Maximum records"),
                               ("scan_truncated", "Scan truncated"), ("diagnostics_truncated", "Diagnostic output truncated"),
                               ("input", "Input scope")):
                lines.append(f"- {label}: {_supplied(scope, key)}")
            lines.append("")
            diagnostics = rows(review.get("diagnostics"))
            if not diagnostics:
                lines += ["No matching diagnostics were recorded within the supplied review scope. "
                          "This is not a finding that the evidence is consistent.", ""]
            for raw in diagnostics:
                diagnostic = _object(raw)
                if diagnostic.get("status") != "diagnostic":
                    lines += ["Unrecognized review entry — not certified:", "", citations.fenced(citations.json_text(raw), "json"), ""]
                    continue
                lines += [f"### {_supplied(diagnostic, 'id')} — {_supplied(diagnostic, 'category')}", "",
                          "**Unverified diagnostic:** " + _supplied(diagnostic, "summary"), "", _supplied(diagnostic, "why"), ""]
                for key, label in (("record_ids", "Witness record IDs — not certified citations"),
                                   ("observed", "Observed conditions"), ("required", "Further review needed")):
                    lines.append(f"- {label}: {_supplied(diagnostic, key)}")
                lines += ["", "Copied witness records and provenance — not certified findings:", "",
                          citations.fenced(citations.json_text(diagnostic.get("records")), "json"), ""]
            if review.get("limitations"):
                lines += ["Review limitations:", ""] + ["- " + citations.text(item) for item in rows(review["limitations"])] + [""]
            if review.get("disclaimer"):
                lines += [citations.text(review["disclaimer"]), ""]
    return lines


def render(run: dict, include_judgments: bool = False) -> str:
    findings = [(number, f) for number, f in enumerate(run["findings"], 1)
                if isinstance(f, dict) and f.get("status") == "verified"]
    unverified = [f for f in run["findings"] if not isinstance(f, dict) or f.get("status") != "verified"]
    L = [f"# Investigation report: {citations.text(run['case']['name'])}", ""]
    stats = run["stats"]
    L += [f"{len(findings)} finding entries recorded as verified, {citations.value(stats, 'rejected')} "
          "proposed claims refused.", ""]
    if include_judgments:
        L += [f"{len(run.get('conclusions', []))} unverified judgments are included in a "
              "separate appendix at the reader's explicit request.", ""]
    L += _audit_summary(run)
    L += _coverage_summary(run)
    L += _workflow_summary(run, findings)
    L += ["", "## Certified findings", "",
          "Each sentence was generated from extracted records and checked by the proof "
          "checker. `strong`: follows from what the artifacts record. `heuristic`: rests on "
          "a stated rule of thumb. Sentences are reproduced without rewording; markup is "
          "escaped for display. This renderer does not independently verify certificates.", ""]
    by_q = OrderedDict()
    for number, f in findings:
        by_q.setdefault(f.get("question") or "(no question given)", []).append((number, f))
    for q, items in by_q.items():
        L += [f"### {citations.text(q)}", ""]
        for number, f in items:
            links = [f"[fact {citations.value(row, 'id')}](#evidence-f{number}-r{index})"
                     for index, row in enumerate(f.get("cited_facts", []), 1)]
            evidence = ", ".join(links) if links else "No copied evidence records were included."
            L.append(f"- **{citations.value(f, 'finding_id')}** ({citations.value(f, 'strength')}; "
                     f"rules {citations.text(', '.join(map(str, f.get('rules', []))))}) "
                     f"{citations.value(f, 'english')} Evidence: {evidence} "
                     f"[Proof record](#proof-f{number}).")
        L.append("")
    if unverified:
        L += ["Entries not marked verified are not displayed as certified findings. Supplied content:", "",
              citations.fenced(citations.json_text(unverified), "json"), ""]
    L += _proof_gaps(run)
    L += _history_summary(run)
    L += ["## Evidence records", "",
          "Every copied citation is shown below, scoped to its finding. Repeated fact IDs "
          "are not merged. Provenance is copied metadata; its presence does not prove the "
          "parser or its interpretation correct. Source offsets and locations appear only "
          "when supplied by the record.", ""]
    conflicts = citations.conflicting_fact_ids([f for _, f in findings])
    for number, f in findings:
        for index, row in enumerate(f.get("cited_facts", []), 1):
            L += citations.evidence_record(f, row, number, index, conflicts)
    L += ["## Proof records", "",
          "These are the bundle's declared claims and embedded proofs. To verify them, use "
          "the independent verifier with the original evidence store.", ""]
    for number, f in findings:
        L += citations.proof_record(f, number)
    if not include_judgments:
        return "\n".join(L) + "\n"
    L += ["## Appendix: unverified investigator conclusions (outside Lean)", "",
          "These are the investigator's judgments, not certified results. Citing certified "
          "findings does not verify an inference, a causal claim, or a device attribution. "
          "The token and consistency checks are limited safeguards, not proofs.", ""]
    for c in run.get("conclusions", []):
        weak = " Rests in part on a heuristic finding." if c.get("rests_on_heuristic") else ""
        L.append(f"- **{citations.value(c, 'conclusion_id')}** (inference, unverified) {citations.value(c, 'text')} "
                 f"(rests on {citations.text(', '.join(map(str, c['finding_ids'])))}){weak}")
    if not run.get("conclusions"):
        L.append("- none recorded")
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Render certified findings; judgments are opt-in.")
    ap.add_argument("run")
    ap.add_argument("--include-judgments", action="store_true",
                    help="append unverified AI judgments, outside the certified report")
    args = ap.parse_args(argv)
    sys.stdout.write(render(json.loads(Path(args.run).read_text()), args.include_judgments))
    return 0


if __name__ == "__main__":
    sys.exit(main())
