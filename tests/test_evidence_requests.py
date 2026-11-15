"""Bounded reader requests create a continuation snapshot, never edit proof facts."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from agent.evidence_requests import bind_config, catalog, collect, recommendations
from extractor import build
from extractor.intake import load_config, sha256_file
from tests.test_intake import IntakeFixture


def records(path):
    data = json.loads(Path(path).read_text())
    return {(row["kind"], data["strings"][str(row["obj"])]): row["id"] for row in data["facts"]}


class EvidenceRequests(IntakeFixture):
    def setUp(self):
        super().setUp()
        self.initial = self.make()
        self.run = self.root / "run"
        self.run.mkdir()
        bind_config(self.run, self.initial["config"], self.initial["facts"])

    def test_actual_dispatch_union_and_continuation_preserve_parent_snapshot(self):
        original_facts = Path(self.initial["facts"]).read_bytes()
        original_config = Path(self.initial["config"]).read_bytes()
        original_binding = (self.run / "intake-config.json").read_bytes()
        result = collect(self.run, "system", "Computer A")
        self.assertEqual(result["status"], "completed", result)
        self.assertTrue(result["continuation_required"])
        self.assertEqual(self.calls, [("inventory", "Computer A"), ("system", "Computer A")])
        self.assertNotEqual(result["facts"], self.initial["facts"])
        self.assertEqual(Path(self.initial["facts"]).read_bytes(), original_facts)
        self.assertEqual(Path(self.initial["config"]).read_bytes(), original_config)
        self.assertEqual((self.run / "intake-config.json").read_bytes(), original_binding)
        old, new = records(self.initial["facts"]), records(result["facts"])
        self.assertLess(set(old), set(new))
        # The new earlier kind moves IDs: continuation must re-query and re-prove.
        self.assertNotEqual(old[("fileSeen", "inventory recorded object")], new[("fileSeen", "inventory recorded object")])
        cfg = load_config(result["config"], verify_images=True)
        self.assertEqual(cfg["parent_facts"]["sha256"], self.initial["facts_sha256"])
        self.assertEqual(cfg["selected"], [{"reader": "inventory", "exhibit": "Computer A"},
                                           {"reader": "system", "exhibit": "Computer A"}])
        self.assertEqual(json.loads((self.run / "latest-collection.json").read_text()), result)
        self.assertEqual(json.loads((Path(result["facts"]).parent / "collection.json").read_text()), result)
        # A separate stage explicitly binds the new config before another reader.
        next_run = self.root / "next-run"
        next_run.mkdir()
        bind_config(next_run, result["config"], result["facts"])
        next_result = collect(next_run, "content", "Computer A")
        self.assertEqual(next_result["status"], "completed", next_result)
        self.assertLess(set(new), set(records(next_result["facts"])))
        self.assertEqual(sha256_file(result["facts"]), result["facts_sha256"])

    def test_duplicate_request_returns_receipt_and_other_request_requires_continuation(self):
        first = collect(self.run, "system", "Computer A")
        again = collect(self.run, "system", "Computer A")
        self.assertTrue(again["reused"])
        self.assertEqual(first["facts"], again["facts"])
        refused = collect(self.run, "content", "Computer A")
        self.assertEqual(refused["status"], "rejected")
        self.assertTrue(refused["continuation_required"])
        self.assertEqual(len(self.calls), 2)
        advice = recommendations(self.run)
        self.assertTrue(advice["continuation_required"])
        self.assertEqual(advice["recommendations"], [])
        self.assertIn("Continue", advice["reason"])

    def test_extension_recomputes_aggregate_tags_and_preserves_source_observations(self):
        def synthetic_reader(name):
            def extract(ev, path, ctx):
                if name == "extractor.inventory":
                    ev.add("emailSent", 10, 1, "Shared subject", "recipient",
                           folder="Deleted Items", **ctx["common"])
                    # A stable derived tag must be recreated once, not carried
                    # forward alongside a second copy at the new examination time.
                    ev.add("webSearch", 20, 1, "recover files", "browser",
                           source="deterministic", **ctx["common"])
                    ev.add("tag", 30, 1, "Shared subject", "source label",
                           source="mailbox label", **ctx["common"])
                    ev.add("tag", 40, 1, "Shared subject", "unclassified source tag", **ctx["common"])
                else:
                    ev.add("emailSent", 50, 1, "Shared subject", "recipient",
                           folder="Sent Items", **ctx["common"])
            return SimpleNamespace(extract=extract)

        with patch.object(build, "import_module", side_effect=synthetic_reader):
            initial = self.make(output="mail-snapshot")
            run = self.root / "mail-run"
            run.mkdir()
            bind_config(run, initial["config"], initial["facts"])
            original = Path(initial["facts"]).read_bytes()
            original_config = Path(initial["config"]).read_bytes()
            result = collect(run, "webcloud", "Computer A")
        self.assertEqual(result["status"], "completed", result)

        def decoded(data):
            return [(row["kind"], row["t"], row["res"],
                     data["strings"][str(row["obj"])] , data["strings"][str(row["aux"])], row["prov"])
                    for row in data["facts"]]

        old_data = json.loads(original)
        new_data = json.loads(Path(result["facts"]).read_text())
        old, new = decoded(old_data), decoded(new_data)
        old_derived = [r for r in old if r[0] == "tag" and r[5].get("source") == "deterministic"]
        new_derived = [r for r in new if r[0] == "tag" and r[5].get("source") == "deterministic"]
        self.assertEqual(len(old_derived), 2)
        self.assertEqual(len(new_derived), 1)
        self.assertEqual(new_derived[0][4], "watch-list-search")
        self.assertNotEqual(new_derived[0][1], next(r[1] for r in old_derived if r[4] == "watch-list-search"))
        self.assertFalse(any(r[0] == "tag" and r[4] == "e-mail in the Deleted Items folder" for r in new))
        for row in old:
            if row not in old_derived:
                self.assertIn(row, new)
        self.assertEqual(sum(r[0] == "emailSent" for r in new), 2)
        refresh = new_data["_meta"]["derived_tag_refresh"]
        self.assertEqual(refresh["discarded_parent_tags"], 2)
        self.assertEqual(refresh["recomputed_tags"], 1)
        self.assertEqual(json.loads(Path(result["health"]).read_text())["derived_tag_refresh"], refresh)
        self.assertNotIn("derived_tag_refresh", old_data["_meta"])
        self.assertEqual(Path(initial["facts"]).read_bytes(), original)
        self.assertEqual(Path(initial["config"]).read_bytes(), original_config)

    def test_no_images_configured_is_a_refusal_not_a_fallback_case(self):
        empty = self.root / "empty-run"
        empty.mkdir()
        response = collect(empty, "system", "Computer A")
        self.assertEqual(response["status"], "rejected")
        self.assertIn("no trusted image intake", response["reason"])
        self.assertEqual(recommendations(empty)["status"], "unavailable")
        self.assertFalse((empty / "evidence-snapshots").exists())

    def test_arbitrary_reader_paths_exhibits_and_wrong_roles_are_refused(self):
        for reader, exhibit in (("../../os", "Computer A"), ("system", "../machine.img"),
                                ("system", str(self.images / "machine.img")), ("media", "Computer A")):
            with self.subTest(reader=reader, exhibit=exhibit):
                response = collect(self.run, reader, exhibit)
                self.assertEqual(response["status"], "rejected", response)
        self.assertEqual(len(self.calls), 1)
        self.assertFalse((self.run / "evidence-snapshots").exists())

    def test_already_selected_reader_cannot_be_repeated_against_same_snapshot(self):
        response = collect(self.run, "inventory", "Computer A")
        self.assertEqual(response["status"], "rejected")
        self.assertIn("already collected", response["reason"])
        self.assertEqual(len(self.calls), 1)

    def test_changed_image_or_fact_snapshot_prevents_collection(self):
        image = self.images / "machine.img"
        original = image.read_bytes()
        image.write_bytes(b"different captured bytes")
        response = collect(self.run, "system", "Computer A")
        self.assertEqual(response["status"], "rejected")
        self.assertIn("image bytes", response["reason"])
        image.write_bytes(original)
        with Path(self.initial["facts"]).open("a") as stream:
            stream.write(" ")
        response = collect(self.run, "system", "Computer A")
        self.assertEqual(response["status"], "rejected")
        self.assertIn("facts snapshot", response["reason"])
        self.assertEqual(len(self.calls), 1)

    def test_parent_facts_changed_during_extraction_prevent_snapshot_publication(self):
        parent = Path(self.initial["facts"])
        original = parent.read_bytes()

        def mutating_reader(ev, path, ctx):
            ev.add("systemSetting", 1, 1, "new observation", "value", **ctx["common"])
            parent.write_bytes(original + b" ")

        with patch.object(build, "import_module", return_value=SimpleNamespace(extract=mutating_reader)):
            response = collect(self.run, "system", "Computer A")
        self.assertEqual(response["status"], "rejected", response)
        self.assertIn("parent facts changed during extraction", response["reason"])
        self.assertFalse((self.run / "latest-collection.json").exists())
        outputs = list((self.run / "evidence-snapshots").iterdir())
        self.assertEqual(len(outputs), 1)
        self.assertFalse((outputs[0] / "facts.json").exists())
        self.assertFalse((outputs[0] / "intake-config.json").exists())

    def test_run_binding_refuses_mismatched_facts_and_existing_or_symlink_config(self):
        other = self.root / "other-run"
        other.mkdir()
        wrong = self.root / "wrong.json"
        wrong.write_text("{}")
        with self.assertRaises(ValueError):
            bind_config(other, self.initial["config"], wrong)
        with self.assertRaises(FileExistsError):
            bind_config(self.run, self.initial["config"], self.initial["facts"])
        (other / "intake-config.json").symlink_to(self.initial["config"])
        with self.assertRaises(FileExistsError):
            bind_config(other, self.initial["config"], self.initial["facts"])

    def test_snapshot_directory_traversal_and_pending_receipt_escape_are_refused(self):
        external = self.root / "external"
        external.mkdir()
        (self.run / "evidence-snapshots").symlink_to(external)
        response = collect(self.run, "system", "Computer A")
        self.assertEqual(response["status"], "rejected")
        self.assertEqual(list(external.iterdir()), [])
        (self.run / "evidence-snapshots").unlink()
        (self.run / "latest-collection.json").write_text(json.dumps({"status": "completed", "config": "/etc/passwd"}))
        response = collect(self.run, "system", "Computer A")
        self.assertEqual(response["status"], "rejected")
        self.assertIn("outside", response["reason"])

    def test_cross_process_lock_marker_is_not_overwritten_or_silently_removed(self):
        marker = self.run / ".evidence-collection.lock"
        marker.write_text("existing process or interrupted operation")
        response = collect(self.run, "system", "Computer A")
        self.assertEqual(response["status"], "rejected")
        self.assertIn("active or was interrupted", response["reason"])
        self.assertEqual(marker.read_text(), "existing process or interrupted operation")
        self.assertEqual(len(self.calls), 1)

    def test_recommendations_use_supported_types_without_promising_to_fix_conflicts(self):
        gap = {"status": "diagnostic", "requirements": [{"category": "wrong_record_type",
            "reason": "need a settings record", "action": "retrieve the actual record",
            "required": {"kind": "systemSetting"}}]}
        result = recommendations(self.run, gap)
        self.assertEqual([(r["reader"], r["exhibit"]) for r in result["recommendations"]], [("system", "Computer A")])
        conflict = {"status": "diagnostic", "requirements": [{"category": "contradictory_identity_or_value",
            "reason": "two different device serials", "action": "review the conflicting identities",
            "required": {"rules": ["R7"]}}]}
        result = recommendations(self.run, conflict)
        self.assertEqual(result["recommendations"], [])
        self.assertTrue(result["evidence_needs"][0]["requires_review"])
        self.assertIn("does not establish", result["note"])
        self.assertTrue(any(r["reader"] == "inventory" and r["already_collected"] for r in catalog(self.run)))
