"""Optional run metadata preserves proof data and keeps missing activity unknown."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from agent.audit import AuditLog, verify_audit
from checker.check import check
from checker.export import bundle
from checker.facts import open_source


FACTS = Path(__file__).resolve().parent.parent / "fixtures/sample_facts.json"


class ExportMetadata(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.fixture.cleanup)
        cls.certificate = check({"searched": [3100]}, "Metadata", open_source(FACTS),
                                "Which search?", Path(cls.fixture.name))
        if cls.certificate["status"] != "verified":
            raise AssertionError(cls.certificate)
        cls.lean = (Path(cls.fixture.name) / "Metadata.lean").read_text()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.write("Metadata.json", self.certificate)
        (self.directory / "Metadata.lean").write_text(self.lean)

    def write(self, name, value):
        path = self.directory / name
        path.write_text(json.dumps(value) + "\n")
        return path

    def proposals(self):
        (self.directory / "proposals.jsonl").write_text(json.dumps(self.certificate) + "\n")

    def audit(self):
        self.proposals()
        log = AuditLog(self.directory / "audit.jsonl")
        log.record("fact", {"fact_id": 3100}, lambda: {"id": 3100})
        log.record("sql", {"query": "SELECT COUNT(*) FROM facts"}, lambda: {"rows": [[9999]]})
        arguments = {"question": "Which search?", "claim": {"searched": [3100]}}
        result = {"status": "verified", "finding_id": "Metadata"}
        log.record("check", arguments, lambda: result)
        log.record("check", arguments, lambda: dict(result, note="already proposed as Metadata"))
        log.record("fact", {"fact_id": 999999}, lambda: {"error": "no such record"})
        return verify_audit(log.path)["head"]

    def test_legacy_pair_keeps_certificate_and_missing_activity_is_unknown(self):
        result = bundle(self.directory, "Legacy")
        expected = dict(self.certificate, lean=self.lean)
        self.assertEqual(result["findings"], [expected])
        self.assertEqual(result["version"], 1)
        self.assertEqual(result["stats"]["proposals"], 0)
        self.assertEqual(result["audit"]["status"], "unavailable")
        self.assertIsNone(result["audit"]["count"])
        self.assertEqual(result["coverage"]["inspection"]["status"], "unmeasured")
        self.assertIsNone(result["coverage"]["inspection"]["record_count"])
        self.assertFalse(result["history"]["available"])
        self.assertEqual(json.loads((self.directory / "Metadata.json").read_text()), self.certificate)

    def test_actual_audit_snapshot_distinguishes_inspection_citations_and_duplicates(self):
        head = self.audit()
        result = bundle(self.directory, "Audited", audit_expected_head=head)
        self.assertTrue(result["audit"]["passed"])
        self.assertEqual(result["audit"]["count"], 5)
        self.assertEqual(result["audit"]["head"], head)
        self.assertEqual(result["audit"]["sha256"], hashlib.sha256(
            (self.directory / "audit.jsonl").read_bytes()).hexdigest())
        self.assertEqual(result["coverage"]["inspection"]["record_ids"], [3100])
        self.assertEqual(result["coverage"]["inspection"]["completed_tool_calls"], 5)
        self.assertEqual(result["coverage"]["citations"]["record_count"], 1)
        self.assertEqual(result["history"]["counts"]["accepted"], 1)
        self.assertEqual(result["history"]["counts"]["duplicate"], 1)
        self.assertEqual(result["stats"]["proposals"], 1)
        self.assertEqual(result["coverage"]["failures"]["tools"]["error_count"], 1)
        json.dumps(result, allow_nan=False)

    def test_tampered_audit_invalidates_inspection_not_the_certificate(self):
        self.audit()
        path = self.directory / "audit.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        rows[0]["result"]["id"] = 9999
        path.write_text("".join(json.dumps(row) + "\n" for row in rows))
        result = bundle(self.directory, "Tampered trace")
        self.assertFalse(result["audit"]["passed"])
        self.assertEqual(result["coverage"]["inspection"]["status"], "invalid")
        self.assertIsNone(result["coverage"]["inspection"]["record_count"])
        self.assertEqual(result["history"]["audit_integrity"]["status"], "failed")
        self.assertEqual(result["findings"], [dict(self.certificate, lean=self.lean)])

    def test_malformed_and_incomplete_logs_remain_diagnostics(self):
        for raw in (b"{incomplete", b"[]\n"):
            with self.subTest(raw=raw):
                (self.directory / "audit.jsonl").write_bytes(raw)
                result = bundle(self.directory, "Malformed trace")
                self.assertEqual(result["audit"]["status"], "invalid")
                self.assertIsNone(result["coverage"]["inspection"]["record_count"])
                self.assertEqual(len(result["findings"]), 1)

    def test_expected_checkpoint_cannot_be_silently_ignored(self):
        missing = bundle(self.directory, "Missing anchored log", audit_expected_head="0" * 64)
        self.assertEqual(missing["audit"]["status"], "invalid")
        self.audit()
        mismatched = bundle(self.directory, "Wrong anchor", audit_expected_head="0" * 64)
        self.assertFalse(mismatched["audit"]["passed"])

    def test_empty_valid_audit_is_distinct_from_missing_audit(self):
        AuditLog(self.directory / "audit.jsonl")
        result = bundle(self.directory, "Empty trace")
        self.assertTrue(result["audit"]["passed"])
        self.assertEqual(result["coverage"]["inspection"]["record_count"], 0)
        self.assertEqual(result["coverage"]["inspection"]["completed_tool_calls"], 0)

    def test_public_sidecars_and_explicit_answers_need_no_reference(self):
        self.write("extraction-metadata.json", {"facts": 12, "by_kind": {"webSearch": 12}, "unparsed": None})
        public = {"schema_version": 2, "case_id": "fixture", "questions": [
            {"id": name, "prompt": "Public question", "answer_schema": {}} for name in ("Q1", "Q2", "Q3")]}
        self.write("questions.json", public)
        for name in ("reference.json", "answers.json", "results.json", "credentials.json"):
            (self.directory / name).write_text("not JSON; must never be read")
        answers = {"schema_version": 2, "case_id": "fixture", "answers": [
            {"question_id": "Q1", "status": "answered", "answer": False},
            {"question_id": "Q2", "status": "unknown"}]}
        result = bundle(self.directory, "Public case", answers=answers)
        self.assertEqual(result["coverage"]["extraction"]["record_count"], 12)
        self.assertEqual(result["coverage"]["failures"]["extraction"]["status"], "unmeasured")
        self.assertEqual(result["coverage"]["questions"]["answered_count"], 1)
        self.assertEqual(result["coverage"]["questions"]["unknown_ids"], ["Q2"])
        self.assertEqual(result["coverage"]["questions"]["missing_ids"], ["Q3"])
        self.assertEqual(bundle(self.directory, "No answers")["coverage"]["questions"]["status"], "unmeasured")

    def test_explicit_metadata_overrides_sidecars_and_manifest_is_recorded_only(self):
        self.write("extraction-metadata.json", {"facts": 1})
        manifest = {"schema_version": 1, "investigator": {"requested_model": "alias", "resolved_model": None}}
        self.write("run-manifest.json", manifest)
        result = bundle(self.directory, "Explicit", facts_metadata={"facts": 2})
        self.assertEqual(result["coverage"]["extraction"]["record_count"], 2)
        self.assertEqual(result["run_manifest"], manifest)
        self.assertIsNone(result["run_manifest"]["investigator"]["resolved_model"])

    def test_case_metadata_is_available_before_coverage_is_computed(self):
        metadata = {"case_id": "fixture", "backend": "offline", "ended": "failure", "exit_code": 1}
        public = {"schema_version": 2, "case_id": "other", "questions": [
            {"id": "Q1", "prompt": "Public question", "answer_schema": {}}]}
        result = bundle(self.directory, "Execution", case_metadata=metadata, public_questions=public)
        self.assertEqual(result["case"]["backend"], "offline")
        self.assertEqual(result["coverage"]["failures"]["run"], {"status": "failed", "ended": "failure"})
        self.assertEqual(result["coverage"]["questions"]["status"], "invalid")
        self.assertNotIn("generated_at", metadata)
        with self.assertRaisesRegex(ValueError, "case metadata must be an object"):
            bundle(self.directory, "Invalid metadata", case_metadata=[])

    def test_lean_paths_cannot_escape_the_run_directory(self):
        changed = copy.deepcopy(self.certificate)
        for name in ("../private.lean", "/private/private.lean", "..\\private.lean"):
            with self.subTest(name=name):
                changed["lean_file"] = name
                self.write("Metadata.json", changed)
                with self.assertRaisesRegex(ValueError, "local .lean"):
                    bundle(self.directory, "Invalid source")

    def test_audit_and_sidecar_symlinks_are_never_followed(self):
        target = self.directory / "absent"
        (self.directory / "audit.jsonl").symlink_to(target)
        result = bundle(self.directory, "Symlinked trace")
        self.assertEqual(result["audit"]["status"], "invalid")
        self.assertFalse(target.exists())
        (self.directory / "questions.json").symlink_to(target)
        with self.assertRaisesRegex(ValueError, "symlink"):
            bundle(self.directory, "Symlinked sidecar")


if __name__ == "__main__":
    unittest.main()
