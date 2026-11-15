"""Explicit input validation and versioned snapshots, without real image parsing."""
import contextlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from extractor import build
from extractor.acquisition import fallback
from extractor.intake import intake, load_config, sha256_file


class IntakeFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.images = self.root / "images"
        self.images.mkdir()
        (self.images / "machine.img").write_bytes(b"synthetic image bytes")
        self.manifest = {"machine.img": {"exhibit": "Computer A", "role": "pc"}, "_time_zone": "UTC"}
        self.calls = []
        self.patches = contextlib.ExitStack()
        self.addCleanup(self.patches.close)
        self.patches.enter_context(patch.object(build, "version", return_value="test-version"))
        self.patches.enter_context(patch.object(build, "resolve", side_effect=lambda p, e, s: fallback(p.name, e["exhibit"])))
        self.patches.enter_context(patch.object(build, "import_module", side_effect=self.module))
        self.patches.enter_context(patch("dissect.target.Target.open", return_value=object()))
        self.patches.enter_context(patch.object(build, "extract_pc", return_value=({"time_zone": "UTC"}, [])))
        self.patches.enter_context(patch.object(build, "extract_media", return_value=[]))

    def module(self, name):
        def extract(ev, path, ctx):
            reader = name.rsplit(".", 1)[-1]
            self.calls.append((reader, ctx["common"]["exhibit"]))
            kinds = {"inventory": "fileSeen", "system": "systemSetting", "content": "fileContent"}
            ev.add(kinds.get(reader, "fileSeen"), 1, 1, reader + " recorded object", "value", **ctx["common"])
        return SimpleNamespace(extract=extract)

    def make(self, *, output="snapshot", **kwargs):
        return intake(self.images, self.manifest, self.root / output, case="Synthetic case",
                      examined_at="2026-01-01T00:00:00+00:00", readers=["inventory"], **kwargs)


class IntakeTests(IntakeFixture):
    def test_windows_reader_gets_the_declared_examination_time(self):
        from datetime import datetime
        from extractor.store import us
        stamp = '2026-01-01T00:00:00+00:00'
        intake(self.images, self.manifest, self.root / 'windows', readers=['windows'], examined_at=stamp)
        self.assertEqual(build.extract_pc.call_args.kwargs['examined_at'], us(datetime.fromisoformat(stamp)))

    def test_narrow_intake_dispatches_only_approved_reader_and_records_hashes_health(self):
        result = self.make()
        self.assertEqual(self.calls, [("inventory", "Computer A")])
        cfg = load_config(result["config"], verify_images=True)
        self.assertEqual(cfg["selected"], [{"reader": "inventory", "exhibit": "Computer A"}])
        self.assertEqual(cfg["facts"]["sha256"], sha256_file(result["facts"]))
        self.assertEqual(cfg["images"][0]["segments"][0]["sha256"], sha256_file(self.images / "machine.img"))
        health = json.loads(Path(result["health"]).read_text())
        self.assertEqual(health["fact_count"], 1)
        self.assertEqual(health["reader_attempts"][0]["reader"], "inventory")
        self.assertEqual(result["status"], "completed")
        self.assertIsNone(cfg["parent_facts"])
        self.assertNotIn("NIST", Path(result["config"]).read_text())

    def test_missing_manifest_image_refused_before_output_creation(self):
        self.manifest["missing.img"] = {"exhibit": "Missing", "role": "removable"}
        with self.assertRaisesRegex(ValueError, "missing"):
            self.make()
        self.assertFalse((self.root / "snapshot").exists())
        self.assertEqual(self.calls, [])

    def test_manifest_is_required_and_roles_exhibits_are_explicit(self):
        bad = [{}, {"machine.img": {"exhibit": "A"}},
               {"machine.img": {"exhibit": "A", "role": "auto"}},
               {"machine.img": {"role": "pc"}},
               {"machine.img": {"exhibit": "../A", "role": "pc"}}]
        for manifest in bad:
            with self.subTest(manifest=manifest), self.assertRaises(ValueError):
                intake(self.images, manifest, self.root / "bad")
        self.assertFalse((self.root / "bad").exists())

    def test_traversal_absolute_paths_and_symlinks_are_refused(self):
        for name in ("../outside.img", "/absolute.img", "C:\\outside.img", "nested/file.img"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                intake(self.images, {name: {"exhibit": "A", "role": "pc"}}, self.root / "bad")
        external = self.root / "external.img"
        external.write_bytes(b"other image")
        (self.images / "link.img").symlink_to(external)
        with self.assertRaises(ValueError):
            intake(self.images, {"link.img": {"exhibit": "A", "role": "pc"}}, self.root / "bad")

    def test_duplicate_exhibit_unsupported_format_and_missing_ewf_segments(self):
        (self.images / "other.img").write_bytes(b"second image")
        with self.assertRaises(ValueError):
            intake(self.images, {"machine.img": {"exhibit": "A", "role": "pc"},
                                  "other.img": {"exhibit": "A", "role": "pc"}}, self.root / "bad")
        (self.images / "code.py").write_text("not an image")
        with self.assertRaisesRegex(ValueError, "unsupported image"):
            intake(self.images, {"code.py": {"exhibit": "A", "role": "pc"}}, self.root / "bad")
        from extractor.optical import EWF_MAGIC
        for name in ("disk.E01", "disk.E03"):
            (self.images / name).write_bytes(EWF_MAGIC[0] + b"dummy")
        with self.assertRaisesRegex(ValueError, "missing segment"):
            intake(self.images, {"disk.E01": {"exhibit": "A", "role": "pc"}}, self.root / "bad")

    def test_existing_output_is_never_overwritten(self):
        result = self.make()
        before = Path(result["facts"]).read_bytes()
        with self.assertRaises(FileExistsError):
            self.make()
        self.assertEqual(Path(result["facts"]).read_bytes(), before)
        self.assertEqual(len(self.calls), 1)

    def test_invalid_reader_and_naive_observation_time_are_refused(self):
        for readers in ([], ["../anything"], ["inventory", "inventory"], ["media"]):
            with self.subTest(readers=readers), self.assertRaises(ValueError):
                intake(self.images, self.manifest, self.root / "bad", readers=readers)
        with self.assertRaisesRegex(ValueError, "timezone"):
            intake(self.images, self.manifest, self.root / "bad", examined_at="2026-01-01")
        self.assertFalse((self.root / "bad").exists())

    def test_reader_exception_retains_partial_records_and_failed_health(self):
        def reader(ev, path, ctx):
            ev.add("fileSeen", 1, 1, "visible before error", "", **ctx["common"])
            raise ValueError("unsupported synthetic artifact")
        with patch.object(build, "import_module", return_value=SimpleNamespace(extract=reader)):
            result = self.make()
        health = json.loads(Path(result["health"]).read_text())
        self.assertEqual(result["status"], "completed_with_limitations")
        self.assertEqual(health["fact_count"], 1)
        self.assertEqual(health["reader_attempts"][0]["status"], "failed")
        self.assertIn("unsupported synthetic artifact", health["issues"][0])

    def test_image_change_during_extraction_prevents_publishing_config(self):
        original = self.module
        def module(name):
            reader = original(name)
            def changed(ev, path, ctx):
                reader.extract(ev, path, ctx)
                (self.images / "machine.img").write_bytes(b"changed")
            return SimpleNamespace(extract=changed)
        with patch.object(build, "import_module", side_effect=module):
            with self.assertRaisesRegex(ValueError, "changed during extraction"):
                self.make()
        self.assertFalse((self.root / "snapshot" / "intake-config.json").exists())

    def test_config_and_fact_tampering_are_refused(self):
        result = self.make()
        facts = Path(result["facts"])
        original = facts.read_bytes()
        facts.write_bytes(original + b" ")
        with self.assertRaisesRegex(ValueError, "facts snapshot"):
            load_config(result["config"])
        facts.write_bytes(original)
        cfg = Path(result["config"])
        data = json.loads(cfg.read_text())
        data["case"] = "changed"
        cfg.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "configuration digest"):
            load_config(cfg)


if __name__ == "__main__":
    unittest.main()
