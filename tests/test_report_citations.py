"""Inspectable citations remain literal, complete, and separate from diagnostics."""
import copy
import html
import json
import re
import unittest

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


if __name__ == "__main__":
    unittest.main()
