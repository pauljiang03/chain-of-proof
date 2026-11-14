"""Portable packages bind complete evidence and regenerate real fixture proofs."""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from agent.audit import AuditLog, verify_audit
from checker.check import check
from checker.export import bundle
from checker.facts import open_source
from verifier.package import build_package, main, verify_package


ROOT = Path(__file__).resolve().parent.parent
FACTS = ROOT / "fixtures/sample_facts.json"


def fingerprint(path):
    content = path.read_bytes()
    return {"sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


class VerificationPackage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        cls.original = cls.root / "source"
        cls.original.mkdir()
        source = open_source(FACTS)
        for finding_id, claim in (("Search", {"searched": [3100]}), ("Census", {"exactly": ["usbInsert", 2]})):
            result = check(claim, finding_id, source, "Fixture question", cls.original)
            if result["status"] != "verified":
                raise AssertionError(result)
        AuditLog(cls.original / "audit.jsonl").record("fact", {"fact_id": 3100}, lambda: {"id": 3100})
        audit = verify_audit(cls.original / "audit.jsonl")
        data = bundle(cls.original, "Portable fixture")
        data["case"].update(model="fixture-model", backend="fixture", facts_sha256=fingerprint(FACTS)["sha256"])
        data["audit"] = {"status": "valid", "passed": True, "head": audit["head"], "count": audit["count"],
                         "sha256": fingerprint(cls.original / "audit.jsonl")["sha256"], "expected_head": None}
        cls.run_data = data
        write(cls.original / "run.json", data)
        write(cls.original / "run-manifest.json", {
            "schema_version": 1, "inputs": {"facts": {"path": "/unused/not-followed", **fingerprint(FACTS)}},
            "software": {"git": {"commit": "fixture-revision", "dirty": False}},
            "investigator": {"requested_model": "fixture-model", "resolved_model": None,
                             "resolved_model_status": "not_observed", "backend": "fixture"}})
        write(cls.original / "questions.json", {
            "schema_version": 2, "case_id": "portable-fixture",
            "questions": [{"id": "Q1", "prompt": "What was recorded?", "answer_schema": {}}]})
        provenance = json.loads((cls.original / "run-manifest.json").read_text())
        provenance["inputs"].update({
            "questions": {"path": "/do-not-follow/questions.json", **fingerprint(cls.original / "questions.json")},
            "prompt": {"path": "/do-not-follow/prompt.md", "bytes": 10, "sha256": "0" * 64},
            "case_profile": {"path": "/do-not-follow/case-profile.json", "bytes": 20, "sha256": "1" * 64}})
        write(cls.original / "run-manifest.json", provenance)
        write(cls.original / "extraction-metadata.json", {"facts": 15, "unparsed": None, "by_kind": {}})
        (cls.original / ".env").write_text("never copy this sibling\n")
        (cls.original / "reference.json").write_text("never copy this sibling either\n")
        (cls.original / "answers.json").write_text("not a package input\n")
        cls.base = cls.root / "package"
        cls.manifest = build_package(cls.original / "run.json", FACTS, cls.base)

    def setUp(self):
        self.temp_case = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_case.cleanup)
        self.case_root = Path(self.temp_case.name)
        self.package = self.case_root / "package"
        shutil.copytree(self.base, self.package)

    def update_manifest(self, name, *, source_role=None):
        path = self.package / "manifest.json"
        manifest = json.loads(path.read_text())
        manifest["files"][name] = fingerprint(self.package / name)
        if source_role:
            manifest["source_bindings"][source_role].update(manifest["files"][name])
        write(path, manifest)
        return manifest

    def test_real_lean_round_trip_and_external_manifest_anchor(self):
        expected = fingerprint(self.package / "manifest.json")["sha256"]
        result = verify_package(self.package, expected)
        self.assertTrue(result["passed"], result)
        self.assertTrue(result["externally_anchored"])
        self.assertEqual(result["certificates"]["verified"], 2)
        self.assertEqual(result["audit"]["count"], 1)
        self.assertIn("not establish", result["scope"])
        self.assertEqual(self.manifest["provenance"]["requested_model"]["value"], "fixture-model")
        self.assertEqual(self.manifest["provenance"]["resolved_model"]["status"], "unknown")
        self.assertEqual(self.manifest["provenance"]["original_code_revision"]["value"], "fixture-revision")

    def test_whole_fact_store_and_only_allowlisted_sidecars_are_exported(self):
        self.assertEqual((self.package / "facts.json").read_bytes(), FACTS.read_bytes())
        cited = {fact["id"] for finding in self.run_data["findings"] for fact in finding["cited_facts"]}
        all_facts = json.loads((self.package / "facts.json").read_text())["facts"]
        self.assertGreater(len(all_facts), len(cited))
        self.assertEqual(self.manifest["facts"]["records"], len(all_facts))
        self.assertEqual((self.package / "run.json").read_bytes(), (self.original / "run.json").read_bytes())
        for name in (".env", "reference.json", "answers.json", "Search.lean", "Census.json"):
            self.assertFalse((self.package / name).exists())
        for name in ("audit.jsonl", "proposals.jsonl", "run-manifest.json", "questions.json", "extraction-metadata.json"):
            self.assertTrue((self.package / name).is_file())
        receipts = self.manifest["provenance"]["original_inputs"]["inputs"]
        self.assertEqual(receipts["questions"], {"status": "packaged_verified", "file": "questions.json"})
        for role in ("prompt", "case_profile"):
            self.assertEqual(receipts[role], {"status": "not_packaged", "file": None})

    def test_public_questions_must_match_the_original_run_manifest_binding(self):
        source = self.case_root / "mismatched-source"
        shutil.copytree(self.original, source)
        for field, bad in (("sha256", "f" * 64), ("bytes", 99999)):
            with self.subTest(field=field):
                provenance = json.loads((self.original / "run-manifest.json").read_text())
                provenance["inputs"]["questions"][field] = bad
                write(source / "run-manifest.json", provenance)
                output = self.case_root / ("refused-" + field)
                with self.assertRaisesRegex(ValueError, "questions binding"):
                    build_package(source / "run.json", FACTS, output)
                self.assertFalse(output.exists())
                write(self.package / "run-manifest.json", provenance)
                self.update_manifest("run-manifest.json")
                result = verify_package(self.package)
                self.assertFalse(result["passed"])
                self.assertIn("questions binding", result["problems"][0])

    def test_file_tampering_is_rejected_before_any_kernel_check(self):
        for name in ("facts.json", "run.json", "report.md", "audit.jsonl", "toolchain.json"):
            with self.subTest(name=name):
                path = self.package / name
                original = path.read_bytes()
                path.write_bytes(original + b"\n")
                with patch("verifier.package.verify_run") as verify:
                    result = verify_package(self.package)
                self.assertFalse(result["passed"])
                self.assertFalse(result["integrity"])
                verify.assert_not_called()
                path.write_bytes(original)

    def test_missing_manifest_and_unlisted_entries_fail_closed(self):
        original = (self.package / "manifest.json").read_bytes()
        (self.package / "manifest.json").unlink()
        self.assertFalse(verify_package(self.package)["passed"])
        (self.package / "manifest.json").write_bytes(original)
        for directory in (False, True):
            extra = self.package / "unlisted"
            extra.mkdir() if directory else extra.write_text("unexpected")
            self.assertFalse(verify_package(self.package)["passed"])
            extra.rmdir() if directory else extra.unlink()

    def test_manifest_path_escapes_are_rejected_without_opening_them(self):
        original = (self.package / "manifest.json").read_bytes()
        outside = self.case_root / "outside.json"
        outside.write_text("do not read")
        from verifier import package as module
        for unsafe in ("../outside.json", str(outside), "subdirectory/file", "./run.json"):
            with self.subTest(path=unsafe):
                manifest = json.loads(original)
                manifest["files"][unsafe] = fingerprint(outside)
                write(self.package / "manifest.json", manifest)
                with patch.object(module, "_open_read", wraps=module._open_read) as reader:
                    result = verify_package(self.package)
                self.assertFalse(result["passed"])
                self.assertFalse(any(Path(call.args[0]).resolve() == outside.resolve() for call in reader.call_args_list))

    def test_symlink_payload_and_bundle_root_are_refused(self):
        target = self.case_root / "outside.json"
        shutil.copyfile(self.package / "run.json", target)
        (self.package / "run.json").unlink()
        (self.package / "run.json").symlink_to(target)
        self.assertFalse(verify_package(self.package)["passed"])
        link = self.case_root / "bundle-link"
        link.symlink_to(self.base, target_is_directory=True)
        self.assertFalse(verify_package(link)["passed"])

    def test_external_checkpoint_rejects_a_replaced_manifest(self):
        with patch("verifier.package.verify_run") as verify:
            result = verify_package(self.package, "0" * 64)
        self.assertFalse(result["passed"])
        self.assertIn("externally retained", result["problems"][0])
        verify.assert_not_called()

    def test_missing_provenance_or_toolchain_declaration_is_not_silently_accepted(self):
        manifest = json.loads((self.package / "manifest.json").read_text())
        del manifest["provenance"]
        write(self.package / "manifest.json", manifest)
        self.assertFalse(verify_package(self.package)["passed"])
        write(self.package / "manifest.json", self.manifest)
        write(self.package / "toolchain.json", {})
        self.update_manifest("toolchain.json")
        result = verify_package(self.package)
        self.assertFalse(result["passed"])
        self.assertIn("toolchain", result["problems"][0])

    def test_legacy_run_has_explicit_unknown_provenance(self):
        legacy = self.case_root / "legacy"
        legacy.mkdir()
        data = copy.deepcopy(self.run_data)
        data.pop("audit")
        data["case"].pop("model")
        data["case"].pop("backend")
        data["coverage"] = {"records_inspected": 0}
        write(legacy / "run.json", data)
        out = self.case_root / "legacy-package"
        manifest = build_package(legacy / "run.json", FACTS, out)
        for name in ("requested_model", "resolved_model", "backend", "original_code_revision"):
            self.assertEqual(manifest["provenance"][name]["status"], "unknown")
        self.assertEqual(manifest["provenance"]["audit"], {"status": "unknown", "count": None, "head": None})
        self.assertEqual(manifest["provenance"]["recorded_summaries"]["coverage"], "recorded_not_independently_verified")
        self.assertTrue(verify_package(out)["passed"])

    def test_census_is_rechecked_even_after_all_file_hashes_are_rebound(self):
        facts_path = self.package / "facts.json"
        facts = json.loads(facts_path.read_text())
        extra = copy.deepcopy(next(row for row in facts["facts"] if row["kind"] == "usbInsert"))
        extra["id"] = 99999
        facts["facts"].append(extra)
        write(facts_path, facts)
        facts_hash = fingerprint(facts_path)
        manifest = self.update_manifest("facts.json", source_role="facts")
        manifest["facts"]["records"] = len(facts["facts"])
        write(self.package / "manifest.json", manifest)
        data = json.loads((self.package / "run.json").read_text())
        data["case"]["facts_sha256"] = facts_hash["sha256"]
        write(self.package / "run.json", data)
        self.update_manifest("run.json", source_role="run")
        provenance = json.loads((self.package / "run-manifest.json").read_text())
        provenance["inputs"]["facts"].update(facts_hash)
        write(self.package / "run-manifest.json", provenance)
        self.update_manifest("run-manifest.json")
        result = verify_package(self.package)
        self.assertTrue(result["integrity"])
        self.assertFalse(result["passed"])
        self.assertEqual(result["certificates"]["failed"], 1)
        self.assertTrue(next(item for item in result["certificates"]["findings"] if item["finding_id"] == "Census")["problems"])

    def test_rebound_report_or_displayed_lean_cannot_claim_certificate_validity(self):
        (self.package / "report.md").write_text("An unsupported assertion.\n")
        self.update_manifest("report.md")
        result = verify_package(self.package)
        self.assertFalse(result["passed"])
        self.assertIn("report differs", result["problems"][0])
        data = copy.deepcopy(self.run_data)
        data["findings"][0]["lean"] = "axiom not_a_proof : False\n"
        write(self.package / "run.json", data)
        self.update_manifest("run.json", source_role="run")
        result = verify_package(self.package)
        self.assertFalse(result["passed"])
        self.assertIn("stored Lean", result["problems"][0])

    def test_saved_verification_counts_must_match_independent_verification(self):
        saved = json.loads((self.package / "verification.json").read_text())
        saved["verified"] = 999
        write(self.package / "verification.json", saved)
        self.update_manifest("verification.json")
        result = verify_package(self.package)
        self.assertFalse(result["passed"])
        self.assertEqual(result["certificates"]["verified"], 2)
        self.assertIn("saved verification summary", result["problems"][0])

    def test_declared_audit_checkpoint_and_chain_integrity_are_both_enforced(self):
        data = json.loads((self.package / "run.json").read_text())
        data["audit"]["head"] = "0" * 64
        write(self.package / "run.json", data)
        self.update_manifest("run.json", source_role="run")
        self.assertIn("audit checkpoint", verify_package(self.package)["problems"][0])
        event = json.loads((self.package / "audit.jsonl").read_text())
        event["result"] = {"id": 99999}
        write(self.package / "audit.jsonl", event)
        self.update_manifest("audit.jsonl")
        result = verify_package(self.package)
        self.assertFalse(result["passed"])
        self.assertIn("audit integrity", result["problems"][0])

    def test_existing_output_and_forged_run_never_export(self):
        with patch("verifier.package.verify_run") as verify, self.assertRaisesRegex(ValueError, "overwrite"):
            build_package(self.original / "run.json", FACTS, self.package)
        verify.assert_not_called()
        invalid = copy.deepcopy(self.run_data)
        invalid["findings"][0]["english"] = "Unsupported assertion."
        path = self.case_root / "invalid-run.json"
        write(path, invalid)
        output = self.case_root / "refused"
        with self.assertRaisesRegex(ValueError, "verification failed"):
            build_package(path, FACTS, output)
        self.assertFalse(output.exists())

    def test_unreadable_database_is_a_controlled_build_failure(self):
        facts = self.case_root / "invalid.duckdb"
        facts.write_bytes(b"not a database")
        output = self.case_root / "invalid-database-package"
        with self.assertRaisesRegex(ValueError, "cannot read the supplied fact store"):
            build_package(self.original / "run.json", facts, output)
        self.assertFalse(output.exists())

    def test_private_reference_disguised_as_public_questions_is_refused(self):
        public = json.loads((self.package / "questions.json").read_text())
        public["questions"][0]["expected"] = "private value"
        write(self.package / "questions.json", public)
        self.update_manifest("questions.json")
        self.assertFalse(verify_package(self.package)["passed"])
        source = self.case_root / "private-input"
        source.mkdir()
        data = copy.deepcopy(self.run_data)
        data.pop("audit")
        write(source / "run.json", data)
        write(source / "questions.json", public)
        with self.assertRaisesRegex(ValueError, "private"):
            build_package(source / "run.json", FACTS, self.case_root / "never-created")

    def test_cli_reports_success_and_failure_exit_status(self):
        new_output = self.case_root / "cli-package"
        with contextlib.redirect_stdout(io.StringIO()) as built:
            code = main(["build", "--run", str(self.original / "run.json"), "--facts", str(FACTS), "--out", str(new_output)])
        self.assertEqual(code, 0)
        self.assertIn(fingerprint(new_output / "manifest.json")["sha256"], built.getvalue())
        with contextlib.redirect_stdout(io.StringIO()) as output:
            code = main(["verify", "--bundle", str(self.package)])
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(output.getvalue())["passed"])
        (self.package / "run.json").write_text("tampered")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["verify", "--bundle", str(self.package)]), 1)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            main(["build", "--run", str(self.original / "run.json"), "--facts", str(FACTS), "--out", str(self.package)])
        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
