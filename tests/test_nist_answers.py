"""The public-contract adapter must derive values from records, never a key."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from eval import nist_answers as adapter


def fact(kind, obj, aux="", t=1_960_000_000_000_000, number=1, **prov):
    return {"id": number, "kind": kind, "obj_text": obj, "aux_text": aux,
            "t": t, "row_sha256": f"{number:064x}", "prov": prov}


def run(*facts):
    predicates = {"systemSetting": "settingRecorded", "webVisit": "visited", "localSearch": "typedInSearchBox",
                  "accountSeen": "accountRecorded", "noteText": "noteFound", "fileDeleted": "fileDeletedAt",
                  "programRun": "programRan", "fileSeen": "fileRecorded"}
    return {"findings": [{"finding_id": f"F{f['id']}", "status": "verified", "strength": "strong",
                           "parts": [{"part": {predicates[f["kind"]]: [f["id"]]}}], "cited_facts": [f]}
                          for f in facts]}


def profile(*ids):
    return {"schema_version": 2, "case_id": "fictional-case", "time_zone": "America/Los_Angeles",
            "questions": [{"id": qid, "prompt": f"Public prompt for {qid}", "answer_schema": {"type": "object"}}
                          for qid in ids]}


def by_id(result):
    return {r["question_id"]: r for r in result["answers"]}


class PublicAnswers(unittest.TestCase):
    def test_different_names_dates_paths_and_email_values_come_from_records(self):
        facts = [fact("systemSetting", "computer name", "ALTERNATE-LAPTOP"),
                 fact("localSearch", "different query", "Windows Explorer search box", number=2),
                 fact("accountSeen", "other.person@example.test", "outlook e-mail", number=3),
                 fact("webVisit", "https://different.test/somewhere", "Example Browser", number=4),
                 fact("noteText", "A completely different note", "Sticky Notes", number=5,
                      artifact=r"D:\Users\Someone\StickyNotes.snt storage some-id stream 3")]
        result = by_id(adapter.generate(run(*facts), profile("Q5", "Q15", "Q17", "Q20", "Q40", "Q41", "Q32")))
        self.assertEqual(result["Q5"]["answer"], {"computer_name": "ALTERNATE-LAPTOP"})
        self.assertEqual(result["Q17"]["answer"]["searches"][0]["keyword"], "different query")
        self.assertEqual(result["Q17"]["answer"]["searches"][0]["timestamp"], adapter.utc(facts[1]["t"]))
        self.assertEqual(result["Q20"]["answer"], {"account": "other.person@example.test"})
        self.assertEqual(result["Q15"]["answer"]["visits"][0]["url"], "https://different.test/somewhere")
        self.assertEqual(result["Q40"]["answer"]["path"], r"D:\Users\Someone\StickyNotes.snt")
        self.assertEqual(result["Q32"]["status"], "unknown")

    def test_bound_metadata_is_never_labelled_a_lean_proved_full_answer(self):
        f = fact("systemSetting", "network address", "192.0.2.9", adapter_description="Test Adapter",
                 dhcp_enabled=False, subnet_mask="255.255.255.0")
        result = by_id(adapter.generate(run(f), profile("Q9")))["Q9"]
        self.assertFalse(result["answer"]["interfaces"][0]["dhcp_enabled"])
        self.assertEqual(result["support"]["/interfaces/0/ip_address"][0]["basis"], "certified_core")
        self.assertEqual(result["support"]["/interfaces/0/dhcp_enabled"][0]["basis"], "bound_provenance")
        self.assertFalse(result["full_answer_lean_certified"])

    def test_no_claim_of_last_user_or_no_third_party_burner_from_missing_records(self):
        result = by_id(adapter.generate(run(fact("accountSeen", "Sam", "windows local account")), profile("Q7", "Q32", "Q54")))
        self.assertTrue(all(r["status"] == "unknown" and "answer" not in r for r in result.values()))

    def test_unverified_findings_and_count_only_rows_do_not_become_answers(self):
        r = run(fact("systemSetting", "computer name", "UNVERIFIED"))
        r["findings"][0]["status"] = "rejected"
        result = adapter.generate(r, profile("Q5"))
        self.assertEqual(result["answers"][0]["status"], "unknown")
        self.assertEqual(result["nonverified_findings_ignored"], 1)
        r["findings"][0]["status"] = "verified"
        r["findings"][0]["parts"] = [{"part": {"exactly": ["systemSetting", 1]}}]
        self.assertEqual(adapter.generate(r, profile("Q5"))["answers"][0]["status"], "unknown")

    def test_conflicting_scalar_settings_are_withheld(self):
        r = run(fact("systemSetting", "computer name", "HOST-A"),
                fact("systemSetting", "computer name", "HOST-B", number=2))
        self.assertEqual(adapter.generate(r, profile("Q5"))["answers"][0]["status"], "unknown")

    def test_semantically_different_timestamps_are_not_substituted(self):
        facts = [fact("noteText", "Test note", "Sticky Notes", artifact=r"D:\Notes\StickyNotes.snt storage id",
                      time_meaning="modified time of this note's storage inside the Sticky Notes file"),
                 fact("programRun", "TEST.EXE", r"D:\TEST.EXE", number=2,
                      time_meaning="last-write time of the registry key; the list keeps no time per program", source="MUICache")]
        result = by_id(adapter.generate(run(*facts), profile("Q11", "Q41")))
        self.assertEqual(result["Q41"]["status"], "unknown")
        self.assertIsNone(result["Q11"]["answer"]["records"][0]["timestamp"])
        self.assertEqual(result["Q11"]["support"]["/records/0/timestamp"][0]["basis"], "bound_provenance")

    def test_distinct_source_records_keep_multiplicity(self):
        r = run(fact("webVisit", "https://example.test", "Browser", artifact="source A"),
                fact("webVisit", "https://example.test", "Browser", number=2, artifact="source B"))
        result = by_id(adapter.generate(r, profile("Q15", "Q13")))
        self.assertEqual(len(result["Q15"]["answer"]["visits"]), 2)
        self.assertEqual(len(result["Q13"]["answer"]["browsers"]), 1)

    def test_explicit_run_case_identity_must_match(self):
        r = run()
        r["case_id"] = "a-different-case"
        with self.assertRaisesRegex(ValueError, "case_id differs"):
            adapter.generate(r, profile("Q5"))

    def test_aggregate_thumbnail_globs_are_not_reported_as_concrete_files(self):
        aggregate = fact("fileSeen", "thumbnail item", "thumbnail cache",
                         artifact=r"D:\Users\Other\Explorer\thumbcache_*.db cache id abc")
        result = by_id(adapter.generate(run(aggregate), profile("Q38")))["Q38"]
        self.assertEqual(result["status"], "unknown")
        concrete = fact("fileSeen", "another item", "thumbnail cache", number=2,
                        artifact=r"D:\Users\Other\Explorer\thumbcache_1024.db cache id def")
        result = by_id(adapter.generate(run(aggregate, concrete), profile("Q38")))["Q38"]
        self.assertEqual(result["answer"]["paths"], [r"D:\Users\Other\Explorer\thumbcache_1024.db"])

    def test_row_hash_required_and_conflicting_fact_ids_rejected(self):
        r = run(fact("systemSetting", "computer name", "HOST-A"))
        r["findings"][0]["cited_facts"][0].pop("row_sha256")
        with self.assertRaisesRegex(ValueError, "row hash"):
            adapter.generate(r, profile("Q5"))
        r = run(fact("systemSetting", "computer name", "HOST-A"),
                fact("systemSetting", "computer name", "HOST-B"))
        with self.assertRaisesRegex(ValueError, "changes across"):
            adapter.generate(r, profile("Q5"))

    def test_expected_answer_profile_is_rejected(self):
        p = profile("Q5")
        p["questions"][0]["expected"] = {"computer_name": "ANSWER-KEY"}
        with self.assertRaisesRegex(ValueError, "public questions"):
            adapter.generate(run(), p)

    def test_cli_refuses_overwrite_and_leaves_sources_unchanged(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            root = Path(tmp)
            source, public, output = root / "run.json", root / "questions.json", root / "answers.json"
            source.write_text(json.dumps(run(fact("systemSetting", "computer name", "SAFE-HOST"))))
            public.write_text(json.dumps(profile("Q5", "Q60")))
            before = source.read_bytes(), public.read_bytes()
            args = ["--run", str(source), "--questions", str(public), "--out", str(output)]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(adapter.main(args), 0)
            first = output.read_bytes()
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                adapter.main(args)
            self.assertEqual(output.read_bytes(), first)
            self.assertEqual((source.read_bytes(), public.read_bytes()), before)


if __name__ == "__main__":
    unittest.main()
