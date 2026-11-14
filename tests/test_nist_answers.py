"""The public-contract adapter must derive values from records, never a key."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from eval import nist_answers as adapter


def fact(kind, obj, aux="", t=1_960_000_000_000_000, number=1, **prov):
    return {"id": number, "kind": kind, "obj_text": obj, "aux_text": aux,
            "t": t, "row_sha256": f"{number:064x}", "prov": prov}


def run(*facts):
    predicates = {"systemSetting": "settingRecorded", "webVisit": "visited", "localSearch": "typedInSearchBox",
                  "accountSeen": "accountRecorded", "noteText": "noteFound", "fileDeleted": "fileDeletedAt",
                  "programRun": "programRan", "fileSeen": "fileRecorded", "fileContent": "contentHashed",
                  "emailSent": "emailed"}
    return {"findings": [{"finding_id": f"F{f['id']}", "status": "verified", "strength": "strong",
                           "parts": [{"part": {predicates[f["kind"]]: [f["id"]]}}], "cited_facts": [f]}
                          for f in facts]}


def profile(*ids):
    return {"schema_version": 2, "case_id": "fictional-case", "time_zone": "America/Los_Angeles",
            "questions": [{"id": qid, "prompt": f"Public prompt for {qid}", "answer_schema": {"type": "object"}}
                          for qid in ids]}


def by_id(result):
    return {r["question_id"]: r for r in result["answers"]}


def container(category, path, number=1, **extra):
    metadata = {"inventory_category": category, "source_path": path,
                "hash_complete": True, "hash_algorithm": "sha256",
                "timestamp_semantics": "examination_observation", "size": 42,
                "file_created_utc": "2030-06-07T08:09:10Z",
                "file_modified_utc": "2031-07-08T09:10:11Z"}
    metadata.update(extra)
    return fact("fileContent", path, "sha256:" + "a" * 64, number=number, **metadata)


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

    def test_program_vocabulary_preserves_execution_modification_and_unreported_times(self):
        rows = [fact("programRun", "ONE.EXE", r"D:\Apps\ONE.EXE", source="prefetch",
                     time_meaning="last run time in the prefetch header", run_count=2),
                fact("programRun", "TWO.EXE", r"D:\Apps\TWO.EXE", number=2, source="UserAssist",
                     time_meaning="last run time stored in the UserAssist entry", run_count=1),
                fact("programRun", "THREE.EXE", r"D:\Apps\THREE.EXE", number=3,
                     source="application compatibility cache", executed_flag=False,
                     time_meaning="last-modified time of the file as stored in the compatibility cache; not a run time"),
                fact("programRun", "FOUR.EXE", r"D:\Apps\FOUR.EXE", number=4, source="MUICache",
                     time_meaning="last-write time of the registry key; the list keeps no time per program"),
                fact("programRun", "FIVE.EXE", r"D:\Apps\FIVE.EXE", number=5,
                     source="application compatibility cache",
                     time_meaning="last-write time of the AppCompatCache key; this entry stores no file time")]
        answer = by_id(adapter.generate(run(*rows), profile("Q11")))["Q11"]
        records = answer["answer"]["records"]
        self.assertEqual([r["source"] for r in records], ["Prefetch", "UserAssist", "Shimcache", "MuiCache", "Shimcache"])
        self.assertEqual([r["time_meaning"] for r in records], ["execution", "execution", "file modification", "unreported", "unreported"])
        self.assertEqual(records[2]["timestamp"], adapter.utc(rows[2]["t"]))
        self.assertIsNone(records[3]["timestamp"])
        self.assertIsNone(records[4]["timestamp"])
        self.assertNotIn("execution_count", records[2])
        semantic_support = answer["support"]["/records/2/time_meaning"]
        self.assertEqual({s["slot"] for s in semantic_support}, {"prov.source", "prov.time_meaning"})
        self.assertTrue(all(s["basis"] == "bound_provenance" for s in semantic_support))

    def test_source_name_alone_does_not_change_timestamp_semantics(self):
        unknown = "file creation time; no time per program is established by this reader"
        rows = [fact("programRun", "OTHER.EXE", r"E:\OTHER.EXE", source="prefetch", time_meaning=unknown),
                fact("programRun", "ANOTHER.EXE", r"E:\ANOTHER.EXE", number=2, source="Unrecognized cache",
                     time_meaning="last run time in the prefetch header")]
        records = by_id(adapter.generate(run(*rows), profile("Q11")))["Q11"]["answer"]["records"]
        self.assertEqual(records[0]["time_meaning"], unknown)
        self.assertIsNotNone(records[0]["timestamp"])
        self.assertEqual(records[1]["source"], "Unrecognized cache")
        self.assertNotEqual(records[1]["time_meaning"], "execution")

    def test_browser_artifacts_accept_explicit_and_legacy_extensionless_files(self):
        rows = [fact("webVisit", "https://one.test", "Other Browser", source_file=r"E:\Profiles\One\History File"),
                fact("webVisit", "https://two.test", "Chrome", number=2,
                     artifact=r"D:\Users\Two\Profile A\History table visits id 81"),
                fact("webVisit", "https://three.test", "Chrome", number=3,
                     artifact=r"D:\Users\Two\Profile A\History Provider Cache entry for history id 7"),
                fact("webVisit", "https://four.test", "Chrome", number=4,
                     artifact=r"D:\Users\Three\Shortcuts table omni_box_shortcuts id 3")]
        answer = by_id(adapter.generate(run(*rows), profile("Q14")))["Q14"]
        self.assertEqual([a["path"] for a in answer["answer"]["artifacts"]],
                         [r"E:\Profiles\One\History File", r"D:\Users\Two\Profile A\History",
                          r"D:\Users\Two\Profile A\History Provider Cache", r"D:\Users\Three\Shortcuts"])
        self.assertEqual(answer["support"]["/artifacts/0/path"][0]["slot"], "prov.source_file")
        self.assertEqual(answer["support"]["/artifacts/0/path"][0]["basis"], "bound_provenance")

    def test_browser_locator_guesses_and_conflicting_explicit_globs_are_not_files(self):
        rows = [fact("webVisit", "https://one.test", "Chrome", artifact=r"D:\Profile\History unexplained text"),
                fact("webVisit", "https://two.test", "Chrome", number=2, source_file=r"D:\Profile\*",
                     artifact=r"D:\Profile\History table visits id 1"),
                fact("webVisit", "https://three.test", "Chrome", number=3, source_file="History")]
        self.assertEqual(adapter.generate(run(*rows), profile("Q14"))["answers"][0]["status"], "unknown")

    def test_unavailable_email_sender_is_omitted_without_owner_substitution(self):
        rows = [fact("emailSent", "Missing property", "from display name to recipient", folder="Sent Items", mailbox_user="Someone"),
                fact("emailSent", "Legacy empty", number=2, sender_address="", attachments=0),
                fact("emailSent", "Explicit empty", number=3, sender_address="", sender_address_status="empty"),
                fact("emailSent", "Available", number=4, sender_address="different@example.test", sender_address_status="present"),
                fact("emailSent", "Unavailable", number=5, sender_address="untrusted@example.test", sender_address_status="unavailable")]
        answer = by_id(adapter.generate(run(*rows), profile("Q21")))["Q21"]
        records = answer["answer"]["messages"]
        self.assertTrue(all("from" not in records[i] for i in (0, 1, 2, 4)))
        self.assertEqual(records[3]["from"], "different@example.test")
        self.assertEqual(records[1]["attachments"], [])
        self.assertNotIn("attachments", records[0])
        self.assertEqual({s["slot"] for s in answer["support"]["/messages/3/from"]},
                         {"prov.sender_address", "prov.sender_address_status"})

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

    def test_inventory_exports_concrete_paths_without_account_enablement_or_time_inference(self):
        facts = [container("outlook_mailbox", r"D:\Profiles\Different\mail.person@example.test.ost"),
                 container("thumbnail_cache", r"D:\Profiles\Different\thumbcache_144.db", number=2),
                 container("sticky_notes", r"E:\Notes\plum.sqlite", number=3),
                 container("windows_search", r"D:\Search\OtherIndex.db", number=4)]
        answers = by_id(adapter.generate(run(*facts), profile("Q19", "Q20", "Q38", "Q40", "Q41", "Q42")))
        self.assertEqual(answers["Q19"]["answer"], {"path_as_printed": facts[0]["obj_text"]})
        self.assertEqual(answers["Q38"]["answer"], {"paths": [facts[1]["obj_text"]]})
        self.assertEqual(answers["Q40"]["answer"], {"path": facts[2]["obj_text"]})
        self.assertEqual(answers["Q42"]["answer"], {"database_path": facts[3]["obj_text"]})
        self.assertEqual(answers["Q20"]["status"], "unknown")
        self.assertEqual(answers["Q41"]["status"], "unknown")
        support = answers["Q40"]["support"]["/path"]
        self.assertTrue(any(s["slot"] == "obj_text" and s["basis"] == "certified_core" for s in support))
        self.assertTrue(any(s["slot"] == "prov.inventory_category" and s["basis"] == "bound_provenance" for s in support))
        self.assertTrue(all(s["set"] == "contentHashed" for s in support))
        self.assertFalse(answers["Q40"]["full_answer_lean_certified"])

    def test_inventory_requires_complete_content_claim_and_consistent_bound_fields(self):
        for metadata in ({"hash_complete": False}, {"hash_algorithm": "md5"},
                         {"source_path": r"D:\Another\database.db"},
                         {"timestamp_semantics": "file_creation"}):
            with self.subTest(metadata=metadata):
                f = container("windows_search", r"D:\Index\Windows.db", **metadata)
                self.assertEqual(adapter.generate(run(f), profile("Q42"))["answers"][0]["status"], "unknown")
        for claim in ({"exactly": ["fileContent", 1]}, {"sameContent": [1, 1]}):
            r = run(container("windows_search", r"D:\Index\Windows.db"))
            r["findings"][0]["parts"] = [{"part": claim}]
            self.assertEqual(adapter.generate(r, profile("Q42"))["answers"][0]["status"], "unknown")
        f = container("windows_search", r"D:\Index\*.db")
        self.assertEqual(adapter.generate(run(f), profile("Q42"))["answers"][0]["status"], "unknown")
        f = container("thumbnail_cache", r"D:\Explorer\thumbcache_512.db", hash_complete=False,
                      artifact=r"filesystem artifact container D:\Explorer\thumbcache_512.db")
        f["kind"] = "fileSeen"
        self.assertEqual(adapter.generate(run(f), profile("Q38"))["answers"][0]["status"], "unknown")

    def test_multiple_inventory_scalars_are_withheld_instead_of_choosing_a_user(self):
        categories = [("outlook_mailbox", "Q19", "mail.pst"),
                      ("sticky_notes", "Q40", "StickyNotes.snt"),
                      ("windows_search", "Q42", "Windows.edb")]
        for category, qid, basename in categories:
            with self.subTest(category=category):
                facts = [container(category, f"D:\\Users\\One\\{basename}"),
                         container(category, f"D:\\Users\\Two\\{basename}", number=2)]
                response = adapter.generate(run(*facts), profile(qid))["answers"][0]
                self.assertEqual(response["status"], "unknown")
                self.assertIn("Multiple supported container paths", response["reason"])

    def test_inventory_cache_list_retains_all_profiles_and_deduplicates_exact_paths(self):
        first = r"D:\Users\One\thumbcache_512.db"
        second = r"D:\Users\Two\thumbcache_512.db"
        r = run(container("thumbnail_cache", second), container("thumbnail_cache", first, number=2),
                container("thumbnail_cache", first, number=3))
        response = adapter.generate(r, profile("Q38"))["answers"][0]
        self.assertEqual(response["answer"]["paths"], [first, second])
        self.assertEqual({s["fact_id"] for s in response["support"]["/paths/0"]}, {2, 3})

    def test_inventory_conflict_with_older_locator_is_not_hidden(self):
        rows = [fact("noteText", "A note", "Sticky Notes", artifact=r"D:\Old\StickyNotes.snt storage id"),
                container("sticky_notes", r"E:\New\plum.sqlite", number=2)]
        self.assertEqual(adapter.generate(run(*rows), profile("Q40"))["answers"][0]["status"], "unknown")

    def test_inventory_joins_do_not_drop_additional_older_locator_conflicts(self):
        rows = [fact("noteText", "A note", "Sticky Notes", artifact=r"D:\Old\StickyNotes.snt storage id"),
                fact("noteText", "Another note", "Sticky Notes", number=2,
                     artifact=r"E:\Other\StickyNotes.snt storage id"),
                container("sticky_notes", r"D:\Old\StickyNotes.snt", number=3)]
        self.assertEqual(adapter.generate(run(*rows), profile("Q40"))["answers"][0]["status"], "unknown")

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

    def test_inventory_reader_to_kernel_verifier_to_public_answers(self):
        from checker.check import check
        from checker.facts import open_source
        from extractor import inventory
        from extractor.store import Evidence
        from tests.test_inventory import FS
        from verifier.verify import verify_run

        fs = FS()
        paths = ["D:/Users/New/AppData/Local/Microsoft/Outlook/example.ost",
                 "D:/Users/New/AppData/Local/Microsoft/Windows/Explorer/thumbcache_512.db",
                 "D:/Users/New/AppData/Roaming/Microsoft/Sticky Notes/StickyNotes.snt",
                 "D:/ProgramData/Microsoft/Search/Data/Applications/Windows/Other.db"]
        for path in paths:
            fs.add(path, data=b"complete container bytes")
        target = SimpleNamespace(fs=fs, user_details=SimpleNamespace(all_with_home=lambda: iter(())))
        evidence = Evidence()
        inventory.extract(evidence, target, {"common": {"image": "fiction.E01", "exhibit": "Computer", "tool": "test"},
                                             "examined_at": 1_960_000_000_000_000})
        self.assertFalse(evidence.problems)
        with tempfile.TemporaryDirectory(dir="/private/tmp") as directory:
            root = Path(directory)
            facts_path = root / "facts.json"
            evidence.write_json(facts_path, {})
            source = open_source(facts_path)
            ids = [f.id for f in source.all()]
            self.assertEqual(len(ids), 4)
            cert = check({"both": [{"contentHashed": [fid]} for fid in ids]}, "InventoryAnswers", source,
                         out_dir=root / "certs")
            self.assertEqual(cert["status"], "verified")
            bundle = {"case": {"case_id": "fictional-case"}, "findings": [cert]}
            self.assertTrue(verify_run(bundle, source)["passed"])
            answers = by_id(adapter.generate(bundle, profile("Q19", "Q20", "Q38", "Q40", "Q41", "Q42")))
        self.assertEqual(answers["Q19"]["answer"], {"path_as_printed": paths[0].replace("/", "\\")})
        self.assertEqual(answers["Q38"]["answer"], {"paths": [paths[1].replace("/", "\\")]})
        self.assertEqual(answers["Q40"]["answer"], {"path": paths[2].replace("/", "\\")})
        self.assertEqual(answers["Q42"]["answer"], {"database_path": paths[3].replace("/", "\\")})
        self.assertEqual(answers["Q20"]["status"], "unknown")
        self.assertEqual(answers["Q41"]["status"], "unknown")

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
