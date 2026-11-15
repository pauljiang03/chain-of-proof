"""Coverage counts describe explicit artifacts without keys or guessed activity."""
import copy
import hashlib
import json
import unittest
import tempfile
from pathlib import Path

from agent.coverage import summarize_coverage


def events(*calls):
    result, previous = [], None
    for index, (tool, arguments, value, outcome) in enumerate(calls, 1):
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"))
        event = {"schema_version": 1, "sequence": index, "call_id": f"call-{index}",
                 "started_at": "2026-11-14T20:00:00Z", "completed_at": "2026-11-14T20:00:01Z",
                 "duration_ns": 1000000000, "tool": tool, "arguments": arguments,
                 "result": value, "result_sha256": hashlib.sha256(encoded.encode()).hexdigest(),
                 "success": outcome == "success", "outcome": outcome,
                 "error": {"type": "RuntimeError"} if outcome == "error" else None,
                 "finding_id": None, "previous_sha256": previous}
        event["event_sha256"] = hashlib.sha256(json.dumps(event, sort_keys=True).encode()).hexdigest()
        previous = event["event_sha256"]
        result.append(event)
    return result


class Coverage(unittest.TestCase):
    def setUp(self):
        self.run = {"case": {"case_id": "sample", "ended": "success"},
                    "stats": {"verified": 999}, "findings": [
                        {"finding_id": "A1", "status": "verified", "cited_facts": [{"id": 1}, {"id": 2}]},
                        {"finding_id": "A2", "status": "verified", "cited_facts": [{"id": 2}, {"id": 3}]},
                        {"finding_id": "A3", "status": "rejected", "cited_facts": [{"id": 999}]}]}
        self.public = {"schema_version": 2, "case_id": "sample", "questions": [
            {"id": f"Q{i}", "prompt": "Public question", "answer_schema": {}} for i in range(1, 6)]}
        self.answers = {"schema_version": 2, "case_id": "sample", "answers": [
            {"question_id": "Q1", "status": "answered", "answer": False},
            {"question_id": "Q2", "status": "answered", "answer": None},
            {"question_id": "Q3", "status": "unknown"},
            {"question_id": "Q4", "status": "unanswered"}]}

    def test_missing_inputs_are_unmeasured_not_zero(self):
        result = summarize_coverage({})
        self.assertIsNone(result["extraction"]["record_count"])
        self.assertIsNone(result["inspection"]["record_count"])
        self.assertIsNone(result["citations"]["record_count"])
        self.assertIsNone(result["certification"]["finding_count"])
        self.assertIsNone(result["questions"]["total_count"])
        self.assertIsNone(result["failures"]["tools"]["error_count"])
        self.assertIsNone(result["failures"]["extraction"]["reader_failure_count"])
        self.assertEqual(result["failures"]["extraction"]["health_report"], "missing")

    def test_real_zeroes_require_supplied_empty_artifacts(self):
        result = summarize_coverage({"findings": []}, facts_metadata={"facts": 0, "by_kind": {}, "unparsed": []}, audit_events=[])
        self.assertEqual(result["extraction"]["record_count"], 0)
        self.assertEqual(result["inspection"]["record_count"], 0)
        self.assertEqual(result["certification"]["finding_count"], 0)
        self.assertEqual(result["citations"]["record_count"], 0)
        self.assertEqual(result["failures"]["extraction"]["reader_failure_count"], 0)

    def test_extract_inspect_cite_and_certify_have_different_counts(self):
        audit = events(("fact", {"id": 1}, {"id": 1, "obj": "sample"}, "success"),
                       ("sql", {"query": "SELECT count(*) FROM facts"}, {"columns": ["count(*)"], "rows": [[100]]}, "success"))
        result = summarize_coverage(self.run, facts_metadata={"facts": 100, "by_kind": {"fileSeen": 100}}, audit_events=audit)
        self.assertEqual([result[name]["record_count"] for name in ("extraction", "inspection", "citations")], [100, 1, 3])
        self.assertEqual(result["certification"]["finding_count"], 2)
        self.assertEqual(result["certification"]["verification"], "not_performed")

    def test_inspection_deduplicates_fact_ids_and_ignores_failed_or_mismatched_reads(self):
        audit = events(("fact", {"id": 1}, {"id": 1}, "success"),
                       ("fact", {"id": 1}, {"id": 1}, "success"),
                       ("fact", {"id": 2}, {"id": 3}, "success"),
                       ("fact", {"id": 4}, {"error": "missing record"}, "error"),
                       ("fact", {"id": True}, {"id": True}, "success"))
        result = summarize_coverage(self.run, audit_events=audit)
        self.assertEqual(result["inspection"]["record_ids"], [1])
        self.assertEqual(result["inspection"]["completed_tool_calls"], 5)
        self.assertEqual(result["failures"]["tools"]["error_count"], 1)

    def test_sql_rows_or_aliased_aggregates_never_claim_full_record_inspection(self):
        audit = events(("sql", {"query": "SELECT id FROM facts"}, {"columns": ["id"], "rows": [[1], [2]]}, "success"),
                       ("sql", {"query": "SELECT COUNT(*) AS id FROM facts"}, {"columns": ["id"], "rows": [[999]]}, "success"))
        result = summarize_coverage(self.run, audit_events=audit)
        self.assertEqual(result["inspection"]["record_count"], 0)
        self.assertEqual(result["inspection"]["by_tool"], {"sql": 2})

    def test_f1_workbench_fact_id_argument_is_supported(self):
        audit = events(("fact", {"fact_id": 12}, {"id": 12}, "success"),
                       ("fact", {"fact_id": 13, "id": 14}, {"id": 13}, "success"))
        self.assertEqual(summarize_coverage(self.run, audit_events=audit)["inspection"]["record_ids"], [12])

    def test_workflow_tools_are_counted_without_inventing_record_inspections(self):
        from agent.audit import AuditLog, verify_audit
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            audit = AuditLog(path)
            for name in ("plan", "update_question", "evidence_needs", "collect", "review"):
                audit.record(name, {}, lambda: {"status": "diagnostic", "id": 999})
            audit.record("fact", {"fact_id": 7}, lambda: {"id": 7})
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            measured = summarize_coverage(self.run, audit_events=rows,
                                           audit_verification=verify_audit(path))
        inspection = measured["inspection"]
        self.assertEqual(inspection["status"], "measured")
        self.assertEqual(inspection["audit_integrity"], "passed")
        self.assertEqual(inspection["completed_tool_calls"], 6)
        self.assertEqual(inspection["record_ids"], [7])
        self.assertEqual(set(inspection["by_tool"]), {"plan", "update_question", "evidence_needs", "collect", "review", "fact"})

    def test_audit_integrity_is_not_implied_by_structurally_valid_events(self):
        audit = events(("fact", {"id": 1}, {"id": 1}, "success"))
        result = summarize_coverage(self.run, audit_events=audit)
        self.assertEqual(result["inspection"]["audit_integrity"], "not_checked")
        verification = {"passed": True, "count": 1, "head": audit[-1]["event_sha256"], "problems": []}
        result = summarize_coverage(self.run, audit_events=audit, audit_verification=verification)
        self.assertEqual(result["inspection"]["audit_integrity"], "passed")
        self.assertEqual(result["inspection"]["record_count"], 1)

    def test_failed_or_wrong_audit_checkpoint_invalidates_counts(self):
        audit = events(("fact", {"id": 1}, {"id": 1}, "success"))
        for verification in ({"passed": False}, {"passed": True, "count": 2, "head": audit[-1]["event_sha256"]},
                             {"passed": True, "count": 1, "head": "wrong"}, {}):
            with self.subTest(verification=verification):
                result = summarize_coverage(self.run, audit_events=audit, audit_verification=verification)
                self.assertEqual(result["inspection"]["status"], "invalid")
                self.assertIsNone(result["inspection"]["record_count"])
                self.assertIsNone(result["failures"]["tools"]["error_count"])

    def test_unreadable_log_with_verification_failure_is_invalid_not_missing(self):
        result = summarize_coverage(self.run, audit_verification={"passed": False})
        self.assertEqual(result["inspection"]["status"], "invalid")

    def test_malformed_or_incomplete_audit_events_are_not_counted(self):
        valid = events(("fact", {"id": 1}, {"id": 1}, "success"))
        bad_events = ["not decoded", [None], [{}]]
        for field, value in (("sequence", True), ("sequence", 2), ("tool", []), ("tool", "unknown_tool"), ("completed_at", None),
                             ("duration_ns", -1), ("previous_sha256", "broken"), ("success", False)):
            changed = copy.deepcopy(valid)
            changed[0][field] = value
            bad_events.append(changed)
        for bad in bad_events:
            with self.subTest(bad=bad):
                result = summarize_coverage(self.run, audit_events=bad)
                self.assertEqual(result["inspection"]["status"], "invalid")
                self.assertIsNone(result["inspection"]["record_count"])

    def test_tool_rejections_and_errors_remain_distinct(self):
        audit = events(("check", {}, {"status": "rejected"}, "rejected"),
                       ("fact", {"id": 1}, None, "error"))
        audit[1]["error"] = {"type": "RuntimeError", "message": "DO NOT COPY"}
        result = summarize_coverage(self.run, audit_events=audit)
        self.assertEqual(result["failures"]["tools"]["rejected_count"], 1)
        self.assertEqual(result["failures"]["tools"]["error_count"], 1)
        self.assertNotIn("DO NOT COPY", json.dumps(result))

    def test_unknown_unanswered_missing_and_literal_false_null_are_distinct(self):
        result = summarize_coverage(self.run, public_questions=self.public, answers=self.answers)["questions"]
        self.assertEqual([result[key] for key in ("total_count", "answered_count", "unknown_count", "unanswered_count", "missing_count")], [5, 2, 1, 1, 1])
        self.assertEqual(result["unknown_ids"], ["Q3"])
        self.assertEqual(result["unanswered_ids"], ["Q4"])
        self.assertEqual(result["missing_ids"], ["Q5"])

    def test_missing_answers_are_not_all_unanswered(self):
        result = summarize_coverage(self.run, public_questions=self.public)["questions"]
        self.assertEqual(result["status"], "unmeasured")
        self.assertEqual(result["total_count"], 5)
        self.assertIsNone(result["missing_count"])

    def test_answer_case_and_duplicate_errors_do_not_yield_counts(self):
        for mutate in (lambda a: a.update(case_id="other"), lambda a: a["answers"].append(a["answers"][0]),
                       lambda a: a["answers"][0].pop("answer")):
            answer = copy.deepcopy(self.answers)
            mutate(answer)
            result = summarize_coverage(self.run, public_questions=self.public, answers=answer)["questions"]
            self.assertEqual(result["status"], "invalid")
            self.assertIsNone(result["answered_count"])

    def test_extra_answer_ids_are_reported_without_grading(self):
        answer = copy.deepcopy(self.answers)
        answer["answers"].append({"question_id": "Q99", "status": "answered", "answer": "extra"})
        result = summarize_coverage(self.run, public_questions=self.public, answers=answer)["questions"]
        self.assertEqual(result["unexpected_ids"], ["Q99"])
        self.assertEqual(result["answered_count"], 2)

    def test_private_reference_fields_are_rejected_and_never_returned(self):
        public = copy.deepcopy(self.public)
        public["questions"][0]["expected"] = "SECRET KEY VALUE"
        result = summarize_coverage(self.run, public_questions=public, answers=self.answers)
        self.assertEqual(result["questions"]["status"], "invalid")
        self.assertNotIn("SECRET KEY VALUE", json.dumps(result))

    def test_reader_crashes_unsupported_sources_warnings_and_other_issues_differ(self):
        health = {"fact_count": 10, "issues": ["pc.E01: reader content: RuntimeError: stopped",
                  "stream 1: ValueError: DestList target is not a supported filesystem path",
                  "Windows.edb: RuntimeWarning: not a clean shutdown", "file: ValueError: bad bytes"]}
        result = summarize_coverage(self.run, health=health)["failures"]["extraction"]
        self.assertEqual([result[key] for key in ("reader_failure_count", "unsupported_source_count", "warning_count", "unclassified_issue_count")], [1, 1, 1, 1])
        self.assertEqual(result["source"], "health.issues")

    def test_unknown_health_metadata_is_not_a_clean_extraction(self):
        for metadata in ({"facts": 10}, {"facts": 10, "unparsed": None}):
            result = summarize_coverage(self.run, facts_metadata=metadata)["failures"]["extraction"]
            self.assertEqual(result["status"], "unmeasured")
            self.assertIsNone(result["reader_failure_count"])

    def test_metadata_issue_report_can_be_measured_while_health_file_is_missing(self):
        result = summarize_coverage(self.run, facts_metadata={"facts": 10, "unparsed": []})["failures"]["extraction"]
        self.assertEqual(result["reader_failure_count"], 0)
        self.assertEqual(result["health_report"], "missing")
        self.assertEqual(result["source"], "facts_metadata.unparsed")

    def test_mismatched_health_population_or_invalid_counts_are_not_combined(self):
        for metadata, health in (({"facts": 10}, {"fact_count": 11, "issues": []}),
                                ({"facts": True}, None), ({"facts": 2, "by_kind": {"a": 1}}, None)):
            result = summarize_coverage(self.run, facts_metadata=metadata, health=health)
            self.assertEqual(result["extraction"]["status"], "invalid")
            self.assertIsNone(result["extraction"]["record_count"])
            self.assertIsNone(result["failures"]["extraction"]["reader_failure_count"])

    def test_absent_citations_are_unknown_and_duplicate_certificates_invalid(self):
        run = {"findings": [{"finding_id": "A1", "status": "verified"}]}
        result = summarize_coverage(run)
        self.assertEqual(result["certification"]["finding_count"], 1)
        self.assertIsNone(result["citations"]["record_count"])
        run["findings"].append(copy.deepcopy(run["findings"][0]))
        result = summarize_coverage(run)
        self.assertEqual(result["certification"]["status"], "invalid")

    def test_run_failure_and_time_budget_are_distinct(self):
        for case, expected in (({}, "unmeasured"), ({"ended": "success"}, "completed"),
                               ({"ended": "time_limit", "exit_code": -9}, "budget_exhausted"),
                               ({"ended": "success", "exit_code": 3}, "failed"),
                               ({"ended": "backend_error"}, "failed"), ({"is_error": True}, "failed")):
            self.assertEqual(summarize_coverage({"case": case})["failures"]["run"]["status"], expected)

    def test_summary_is_json_serializable_and_does_not_mutate_inputs(self):
        before = copy.deepcopy((self.run, self.public, self.answers))
        result = summarize_coverage(self.run, public_questions=self.public, answers=self.answers)
        json.dumps(result, allow_nan=False)
        self.assertEqual((self.run, self.public, self.answers), before)
        self.assertNotIn("answer", result["questions"])


if __name__ == "__main__":
    unittest.main()
