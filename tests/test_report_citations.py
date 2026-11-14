"""Inspectable citations remain literal, complete, and separate from diagnostics."""
import copy
import hashlib
import html
import json
from pathlib import Path
import re
import tempfile
import unittest

from agent.audit import AuditLog, verify_audit
from agent.coverage import summarize_coverage
from agent.history import summarize_history
from checker import citations, report


def fact(number=7001, **overrides):
    row = {"id": number, "kind": "lnkTarget", "t": 1_960_000_000_123_456, "res": 2_000_000,
           "obj": 20, "obj_text": r"D:\Case Files\[project]_review.docx", "aux": 21,
           "aux_text": "VOLUME-OTHER", "row_sha256": "a" * 64,
           "prov": {"image": "different.E01", "exhibit": "USB Z",
                    "artifact": f"shortcut {number}", "offset": 4096 + number,
                    "time_meaning": "shortcut record modification, not proof of a copy",
                    "parser": "fixture parser", "tool": "test tool 1.0"}}
    row.update(overrides)
    return row


def finding(name="F7", rows=None, **overrides):
    result = {"finding_id": name, "status": "verified", "question": "Which file is recorded?",
              "english": r"A record names D:\Case Files\[project]_review.docx; it does not prove a copy.",
              "strength": "strong", "rules": ["R3"], "cited_facts": [fact()] if rows is None else rows,
              "claim": {"opened": [7001]}, "trust_tier": "kernel", "axioms": [],
              "lean": "-- synthetic source for rendering tests only\nexample : True := by trivial\n"}
    result.update(overrides)
    return result


def run(*findings, rejections=(), conclusions=()):
    return {"case": {"name": "Synthetic rendering fixture"},
            "stats": {"verified": len(findings), "rejected": len(rejections)},
            "findings": list(findings), "rejections": list(rejections), "conclusions": list(conclusions)}


def outside_fences(markdown):
    """Inspect emitted markup; literal proof/provenance blocks are intentionally raw."""
    lines, opening = [], None
    for line in markdown.splitlines():
        if opening:
            if line == opening:
                opening = None
        elif re.fullmatch(r"`{3,}[a-z]*", line):
            opening = re.match(r"`+", line)[0]
        else:
            lines.append(line)
    if opening:
        raise AssertionError("unclosed code fence")
    return "\n".join(lines)


def logged_calls(*calls):
    """Use the real log format; these are synthetic tool returns, not proofs."""
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "audit.jsonl"
        log = AuditLog(path)
        for tool, arguments, result in calls:
            def action(result=result):
                if isinstance(result, Exception):
                    raise result
                return result
            try:
                log.record(tool, arguments, action)
            except RuntimeError:
                pass
        verification = verify_audit(path)
        raw = path.read_bytes()
        return [json.loads(line) for line in raw.splitlines()], verification, hashlib.sha256(raw).hexdigest()


def public_questions():
    return {"schema_version": 2, "case_id": "sample", "questions": [
        {"id": f"Q{i}", "prompt": "Synthetic public question", "answer_schema": {}}
        for i in range(1, 6)]}


class ReportCitations(unittest.TestCase):
    def test_every_cited_row_has_a_working_scoped_target_and_full_provenance(self):
        rows = [fact(number) for number in (7001, 7002, 7003, 7004)]
        f = finding(rows=rows)
        data = run(f)
        before = copy.deepcopy(data)
        rendered = report.render(data)
        targets = re.findall(r'\]\(#([^\)]+)\)', rendered)
        anchors = re.findall(r'<a id="([^"]+)"></a>', rendered)
        self.assertEqual(targets, [f"evidence-f1-r{i}" for i in range(1, 5)] + ["proof-f1"])
        self.assertEqual(set(targets), set(anchors))
        self.assertEqual(len(anchors), len(set(anchors)))
        plain = html.unescape(rendered)
        for row in rows:
            self.assertIn(f"### Fact {row['id']} — finding F7", plain)
            self.assertIn(json.dumps(row["prov"], sort_keys=True, ensure_ascii=False, indent=2), rendered)
        for value in ["different.E01", "USB Z", "fixture parser", "test tool 1.0", "a" * 64,
                      "2000000 microseconds", "1960000000123456 microseconds"]:
            self.assertIn(value, plain)
        self.assertIn(f["english"], plain)
        self.assertIn(f["lean"], rendered)
        self.assertNotIn("(+", rendered)
        self.assertEqual(data, before)

    def test_untrusted_metadata_ids_sentences_and_proofs_cannot_inject_markup(self):
        attack = '<img src=x onerror=alert(1)> [open](javascript:alert(2)) & <script>x</script>'
        proof = '-- comment\n```\n<img src=x onerror=alert(3)>\n````\n'
        row = fact(id="fact](https://evil.test)", prov={"artifact": attack, "offset": attack})
        f = finding('F7" onclick="alert(4)', [row], question=attack, english=attack, lean=proof)
        data = run(f)
        data["case"]["name"] = attack
        data["stats"]["verified"] = attack
        rendered = report.render(data)
        visible_markup = outside_fences(rendered)
        self.assertNotIn("<img", visible_markup)
        self.assertNotIn("<script", visible_markup)
        self.assertNotIn("javascript:", visible_markup)
        self.assertNotIn("](https://", visible_markup)
        self.assertEqual(re.findall(r'<[^>]*>', visible_markup),
                         ['<a id="evidence-f1-r1">', '</a>', '<a id="proof-f1">', '</a>'])
        self.assertIn(attack, html.unescape(visible_markup))  # Text preserved, not interpreted as markup.
        self.assertIn("`````lean\n" + proof + "\n`````", rendered)
        self.assertIn("#evidence-f1-r1", rendered)

    def test_missing_provenance_or_embedded_proof_does_not_create_source_locations(self):
        row = fact()
        row.pop("prov")
        row.pop("res")
        row.pop("row_sha256")
        f = finding(rows=[row], lean="", lean_file="../../missing-proof.lean")
        rendered = html.unescape(report.render(run(f)))
        self.assertIn("Image: Not recorded; exhibit: Not recorded", rendered)
        self.assertIn("Timestamp meaning: Not recorded", rendered)
        self.assertIn("Row SHA-256: Not recorded", rendered)
        self.assertIn("Embedded Lean source was not included", rendered)
        self.assertNotIn("missing-proof.lean", rendered)
        self.assertNotIn("4096", rendered)
        self.assertNotIn('"offset"', rendered)
        self.assertIn('[Proof record](#proof-f1)', rendered)

    def test_conflicting_same_id_rows_and_duplicate_finding_ids_remain_separate(self):
        first = fact()
        second = fact(obj_text="a different value", row_sha256="b" * 64,
                      prov={"image": "other.E01", "artifact": "different source"})
        rendered = report.render(run(finding("SAME", [first]), finding("SAME", [second])))
        self.assertIn("#evidence-f1-r1", rendered)
        self.assertIn("#evidence-f2-r1", rendered)
        self.assertIn("#proof-f1", rendered)
        self.assertIn("#proof-f2", rendered)
        self.assertEqual(rendered.count("**Conflicting copied rows share this fact ID.**"), 2)
        self.assertIn("a different value", rendered)
        self.assertIn("a" * 64, rendered)
        self.assertIn("b" * 64, rendered)
        self.assertIn('"image": "other.E01"', rendered)
        identical = report.render(run(finding("FIRST", [first]), finding("SECOND", [first])))
        self.assertNotIn("Conflicting copied rows", identical)
        self.assertIn("#evidence-f2-r1", identical)

    def test_proof_gaps_are_diagnostic_and_never_become_certified_findings_or_repairs(self):
        gap = {"status": "diagnostic", "summary": "The volume identities differ.",
               "requirements": [{"category": "contradictory_identity_or_value",
                                  "reason": "The required identity relation failed.",
                                  "action": "Obtain independent device-to-volume evidence.",
                                  "fact_ids": [7001, 9000], "observed": {"left": "A", "right": "B"},
                                  "required": {"failed_condition": "link 7001 aux 9000 aux"}}],
               "disclaimer": "This diagnostic is not a certified claim."}
        rejections = [{"finding_id": "X1", "status": "rejected", "proof_gap": gap},
                      {"finding_id": "X2", "status": "rejected", "reason": "Do not invent a repair from this text."},
                      {"finding_id": "X3", "status": "rejected", "proof_gap": {"status": "certified", "summary": "NOT A CERTIFICATE"}}]
        conclusion = {"conclusion_id": "C1", "text": "An unverified interpretation.", "finding_ids": ["F7"]}
        data = run(finding(), rejections=rejections, conclusions=[conclusion])
        rendered = html.unescape(report.render(data))
        certified = rendered.split("## Certified findings", 1)[1].split("## Not established", 1)[0]
        self.assertNotIn("X1", certified)
        self.assertIn("(diagnostic, not certified)", rendered)
        self.assertIn("Refusal does not establish", rendered)
        self.assertIn("link 7001 aux 9000 aux", rendered)
        self.assertNotIn("Do not invent a repair", rendered)
        self.assertNotIn("NOT A CERTIFICATE", rendered)
        self.assertNotIn("unverified interpretation", rendered)
        opted_in = html.unescape(report.render(data, include_judgments=True))
        self.assertIn("## Appendix: unverified investigator conclusions (outside Lean)", opted_in)
        self.assertIn("An unverified interpretation.", opted_in)

    def test_diagnostic_fields_are_also_literal_and_no_gap_section_is_invented(self):
        self.assertNotIn("## Not established", report.render(run(finding())))
        attack = '<a href="https://evil.test">fake</a> [x](javascript:evil)'
        gap = {"status": "diagnostic", "summary": attack,
               "requirements": [{"category": attack, "reason": attack, "action": attack,
                                  "observed": attack, "required": attack, "fact_ids": [attack]}],
               "disclaimer": attack}
        rendered = outside_fences(report.render(run(rejections=[{"finding_id": attack, "proof_gap": gap}])))
        self.assertNotIn("<a href", rendered)
        self.assertNotIn("javascript:", rendered)
        self.assertIn(attack, html.unescape(rendered))

    def test_actual_coverage_and_audit_helpers_render_distinct_counts_and_answer_presence(self):
        data = run(finding(rows=[fact(7001), fact(7002), fact(7003)]))
        data["case"].update(case_id="sample", ended="success")
        events, verified, digest = logged_calls(
            ("fact", {"fact_id": 7001}, fact()),
            ("sql", {"query": "SELECT count(*) FROM facts"}, {"rows": [[12]]}),
            ("check", {"claim": {}}, {"status": "rejected"}),
            ("fact", {"fact_id": 9000}, RuntimeError("message must not enter log")))
        self.assertTrue(verified["passed"])
        answers = {"schema_version": 2, "case_id": "sample", "answers": [
            {"question_id": "Q1", "status": "answered", "answer": False},
            {"question_id": "Q2", "status": "answered", "answer": None},
            {"question_id": "Q3", "status": "unknown"},
            {"question_id": "Q4", "status": "unanswered"}]}
        data["coverage"] = summarize_coverage(
            data, facts_metadata={"facts": 12, "by_kind": {"lnkTarget": 12}},
            audit_events=events, audit_verification=verified,
            public_questions=public_questions(), answers=answers,
            health={"fact_count": 12, "issues": ["pc.E01: reader content: RuntimeError: stopped",
                    "source is not supported", "RuntimeWarning: partial source"]})
        data["audit"] = {"status": "valid", "path": "audit.jsonl", "sha256": digest,
                         "expected_head": None, "scope": "Recorded completed tool calls", **verified}
        before = copy.deepcopy(data)
        markdown = report.render(data)
        plain = html.unescape(markdown)
        for row in ("| Extracted records | 12 | measured |",
                    "| Records explicitly returned by the fact tool | 1 | measured |",
                    "| Distinct cited records | 3 | measured |",
                    "| Findings recorded as accepted | 1 | measured |"):
            self.assertIn(row, plain)
        self.assertIn("total 5; answered 2; unknown 1; unanswered 1; missing response 1", plain)
        self.assertIn("Tool outcomes (measured): errors 1; refused calls 1", plain)
        self.assertIn("reader failures 1; unsupported sources 1; warnings 1", plain)
        self.assertIn("Inspection audit integrity: passed", plain)
        self.assertIn("bundle reports a passed audit integrity check", plain)
        self.assertIn("Answer presence is not answer accuracy", plain)
        self.assertIn("Expected head supplied to audit check: not supplied", plain)
        self.assertIn(digest, plain)
        self.assertNotIn("](audit.jsonl)", markdown)
        self.assertLess(plain.index("## Recorded coverage"), plain.index("## Certified findings"))
        self.assertEqual(report.render(data), markdown)
        self.assertEqual(data, before)

    def test_optional_absent_unknown_and_measured_zero_are_different(self):
        data = run()
        absent = report.render(data)
        for heading in ("## Audit integrity", "## Recorded coverage", "## Recorded claim attempts"):
            self.assertNotIn(heading, absent)
        data["coverage"] = summarize_coverage({}, public_questions=public_questions())
        data["history"] = summarize_history(None)
        data["audit"] = {"status": "unavailable", "passed": None, "count": None, "path": None}
        unknown = html.unescape(report.render(data))
        self.assertIn("| Extracted records | unmeasured | unmeasured |", unknown)
        self.assertIn("total 5; answered unmeasured", unknown)
        self.assertIn("Recorded counts: attempts unmeasured; accepted unmeasured", unknown)
        self.assertIn("History is unavailable; this does not establish that no attempts occurred", unknown)
        self.assertIn("Recorded events: unmeasured", unknown)
        data["coverage"] = summarize_coverage(data, facts_metadata={"facts": 0, "by_kind": {}, "unparsed": []}, audit_events=[])
        data["history"] = summarize_history([])
        measured = html.unescape(report.render(data))
        self.assertIn("| Extracted records | 0 | measured |", measured)
        self.assertIn("| Records explicitly returned by the fact tool | 0 | measured |", measured)
        self.assertIn("Recorded counts: attempts 0; accepted 0", measured)
        self.assertIn("Inspection audit integrity: not_checked", measured)
        data["coverage"] = {"schema_version": 99}
        data["history"] = {"schema_version": 99}
        unsupported = report.render(data)
        self.assertEqual(unsupported.count("unavailable or has an unsupported schema"), 2)

    def test_actual_history_keeps_recorded_order_explicit_revisions_and_all_outcomes(self):
        old = {"finding_id": "Z999", "status": "rejected", "claim": {"searched": [7001]}}
        new = {"finding_id": "A001", "status": "verified", "claim": {"searched": [7002]}}
        events, verified, _ = logged_calls(
            ("check", {"question": "Synthetic question", "claim": old["claim"]}, {"finding_id": "Z999", "status": "rejected"}),
            ("check", {"question": "Synthetic question", "claim": new["claim"], "revises": "Z999"}, {"finding_id": "A001", "status": "verified"}),
            ("check", {"question": "Synthetic question", "claim": new["claim"]}, {"finding_id": "A001", "status": "verified", "note": "already proposed as A001"}),
            ("check", {"question": "Synthetic question", "claim": {}}, RuntimeError("not retained")),
            ("check", {"question": "Synthetic question", "claim": {}}, None))
        data = run()
        data["history"] = summarize_history([old, new], events, verified)
        self.assertEqual([a["status"] for a in data["history"]["attempts"]],
                         ["refused", "accepted", "duplicate", "failed", "unknown"])
        before = copy.deepcopy(data)
        plain = html.unescape(report.render(data))
        self.assertIn("attempts 5; accepted 1; refused 1; duplicate 1; failed 1; unknown 1", plain)
        self.assertIn("revises Z999; status valid", plain)
        self.assertIn("duplicate of A001 (no new proof)", plain)
        self.assertIn("| Recorded error | | RuntimeError |", plain)
        self.assertLess(plain.index("| audit:1 | Z999 | refused |"), plain.index("| audit:2 | A001 | accepted |"))
        self.assertIn("Audit order is completed-event order", plain)
        self.assertIn("interrupted calls: unmeasured", plain)
        self.assertIn("No revision or repair is inferred from similar claims", plain)
        self.assertEqual(data, before)

    def test_partial_history_keeps_unknown_placement_and_invalid_revision_visible(self):
        old = {"finding_id": "Z999", "status": "rejected", "claim": {"searched": [7001]}}
        new = {"finding_id": "A001", "status": "verified", "claim": {"searched": [7001]}}
        events, _, _ = logged_calls(("check", {"question": "Synthetic question", "claim": new["claim"], "revises": "unknown-id"},
                                      {"finding_id": "A001", "status": "verified"}))
        data = run()
        data["history"] = summarize_history([old, new], events)
        plain = html.unescape(report.render(data))
        self.assertIn("attempts 1; accepted 1; refused 0", plain)
        self.assertIn("revises unknown-id; status invalid", plain)
        self.assertIn("Unmatched proposal rows: 1", plain)
        self.assertLess(plain.index("## Recorded claim attempts"),
                        plain.index("### Proposals with unknown placement relative to audit events"))
        sequence, unmatched = plain.split("### Proposals with unknown placement relative to audit events", 1)
        self.assertNotIn("| Z999 | refused |", sequence)
        self.assertIn("| Z999 | refused | unavailable / unavailable | none recorded |", unmatched)
        self.assertIn("These rows are separate from the attempt sequence and its counts", unmatched)

    def test_failed_integrity_is_conspicuous_and_invalid_counts_are_not_zero(self):
        events, _, _ = logged_calls(("fact", {"id": 7001}, fact()))
        data = run()
        data["audit"] = {"status": "invalid", "passed": False, "count": 1,
                         "path": "audit.jsonl", "problems": ["event digest mismatch"]}
        data["coverage"] = summarize_coverage(data, audit_events=events, audit_verification={"passed": False})
        data["history"] = summarize_history([], events, {"passed": False})
        plain = html.unescape(report.render(data))
        self.assertIn("**INVALID AUDIT — recorded events are diagnostic only.**", plain)
        self.assertIn("**INVALID HISTORY AUDIT — these events are diagnostic only.**", plain)
        self.assertIn("| Records explicitly returned by the fact tool | invalid | invalid |", plain)
        self.assertIn("Tool outcomes (invalid): errors invalid; refused calls invalid", plain)
        self.assertIn("event digest mismatch", plain)
        self.assertNotIn("bundle reports a passed audit integrity check", plain)

    def test_optional_summary_metadata_cannot_create_html_links_or_table_cells(self):
        attack = '<script>x</script> [x](javascript:evil) | table\n## forged'
        data = run()
        data["audit"] = {"status": "invalid", "passed": False, "path": attack, "scope": attack,
                         "head": attack, "sha256": attack, "expected_head": attack, "problems": [attack]}
        data["coverage"] = summarize_coverage({})
        data["coverage"]["questions"]["missing_ids"] = [attack]
        data["coverage"]["limitations"] = [attack]
        data["coverage"]["failures"]["extraction"]["issues"] = [{"category": attack, "message": attack}]
        data["history"] = summarize_history(None)
        data["history"]["attempts"] = [{"attempt_id": attack, "finding_id": attack, "status": attack,
            "started_at": attack, "completed_at": attack, "revises": attack, "revision_status": attack,
            "revision_error": attack, "error": attack, "problems": [attack]}]
        data["history"]["problems"] = [attack]
        visible = outside_fences(report.render(data))
        self.assertNotIn("<script", visible)
        self.assertNotIn("javascript:", visible)
        self.assertNotIn("\n## forged", visible)
        self.assertNotIn("| table", visible)
        self.assertIn(attack.replace("\n", r"\u000a"), html.unescape(visible))


if __name__ == "__main__":
    unittest.main()
