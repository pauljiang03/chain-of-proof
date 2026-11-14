"""Acquisition identities come from scoped evidence, never filename-specific answers."""
import contextlib
from datetime import datetime
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

from checker.check import check
from checker.facts import JsonFacts
from extractor import acquisition as a, build, content, media, optical
from extractor.fatcarve import Directory, Entry
from extractor.store import Evidence


class AcquisitionIdentity(unittest.TestCase):
    def resolve(self, header, role="removable", supplied=None, disc=False):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "capture.E01"
            path.write_bytes(optical.EWF_MAGIC[0])
            exhibit = {"exhibit": "Custom device", "role": role}
            if supplied:
                exhibit["device_serial"] = supplied
            with patch.object(optical, "ewf_header", return_value=header), \
                 patch.object(optical, "is_optical", return_value=disc):
                return a.resolve(path, exhibit, "shared public manifest")

    def test_only_typed_removable_acquisition_serial_is_used(self):
        identity = self.resolve({"_section": "header2", "sn": " SERIAL-A ", "md": "USB Flash"})
        self.assertEqual(identity["device_identity"], "SERIAL-A")
        self.assertEqual(identity["hardware_serial"], "SERIAL-A")
        self.assertIn("header2 sn field", identity["device_identity_source"])
        for header in ({}, {"a": "SERIAL-A"}, {"volume_serial": "SERIAL-A"},
                       {"sn": "unknown"}, {"sn": "bad\nserial"}):
            with self.subTest(header=header):
                self.assertIsNone(self.resolve(header)["hardware_serial"])

    def test_optical_drive_serial_never_becomes_disc_or_usb_identity(self):
        for role, disc, model in (("optical", True, "DVD+-RW GT80N"),
                                  ("removable", True, "Unspecified drive"),
                                  ("removable", False, "DVD+-RW GT80N"),
                                  ("pc", False, "Hard disk")):
            with self.subTest(role=role, disc=disc, model=model):
                identity = self.resolve({"sn": "DRIVE-SERIAL", "md": model}, role,
                                        supplied="DRIVE-SERIAL", disc=disc)
                self.assertIsNone(identity["hardware_serial"])
                self.assertEqual(identity["device_identity_kind"], "exhibit_image")
                self.assertNotEqual(identity["device_identity"], "DRIVE-SERIAL")

    def test_explicit_shared_manifest_supported_but_conflicts_withheld(self):
        for header in ({}, {"sn": "PUBLIC-SERIAL"}):
            identity = self.resolve(header, supplied="PUBLIC-SERIAL")
            self.assertEqual(identity["device_identity"], "PUBLIC-SERIAL")
            self.assertEqual(identity["device_identity_source"], "shared public manifest")
        identity = self.resolve({"sn": "HEADER-SERIAL"}, supplied="OTHER-SERIAL")
        self.assertIsNone(identity["hardware_serial"])
        self.assertTrue(any("conflict" in note for note in identity["identity_notes"]))

    def test_unreadable_image_type_does_not_promote_header_serial(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "capture.E01"
            path.write_bytes(optical.EWF_MAGIC[0])
            with patch.object(optical, "ewf_header", return_value={"sn": "SERIAL"}), \
                 patch.object(optical, "is_optical", side_effect=ValueError("unreadable")):
                identity = a.resolve(path, {"exhibit": "E", "role": "removable"})
            self.assertIsNone(identity["hardware_serial"])

    def test_same_filename_in_another_case_cannot_load_builtin_serial(self):
        manifest = json.loads(Path(media.__file__).with_name("exhibits.json").read_text())
        self.assertTrue(all("device_serial" not in row for row in manifest.values() if isinstance(row, dict)))
        ctx = {"common": {"image": "rm1.E01", "exhibit": "Other case device", "tool": "test"},
               "examined_at": 42}
        target = NS(path="rm1.E01", os="other")
        with patch.object(optical, "emit_image_digests"), patch.object(optical, "is_optical", return_value=False), \
             patch.object(content, "_removable") as removable, \
             patch.object(Path, "read_text", side_effect=AssertionError("no manifest reads")):
            content.extract(Evidence(), target, ctx)
        identity = removable.call_args.args[3]
        self.assertIsNone(identity["hardware_serial"])
        self.assertIn("Other case device", identity["device_identity"])
        self.assertNotEqual(identity["device_identity"], a.fallback("rm1.E01", "RM#1")["device_identity"])

    def test_build_resolves_once_and_passes_same_context_to_both_readers(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / "custom.E01").write_bytes(b"capture")
            manifest = directory / "manifest.json"
            policy = {"source": "shared brief", "authorized_device_serials": ["CUSTOM-USB"]}
            manifest.write_text(json.dumps({"custom.E01": {"exhibit": "Custom", "role": "removable"},
                                             "_policy": policy}))
            identity = a.fallback("custom.E01", "Custom")
            with patch.object(build, "resolve", return_value=identity) as resolver, \
                 patch.object(build, "extract_media", return_value=[]) as media_reader, \
                 patch.object(build, "import_module") as importer, patch.object(build, "add_tags", return_value=0) as tagger, \
                 patch.object(build, "version", return_value="test"), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(build.main([str(directory), "--exhibits", str(manifest),
                                             "--case", "Custom case", "--out", str(directory / "facts.json")]), 0)
            resolver.assert_called_once()
            self.assertIs(media_reader.call_args.kwargs["acquisition"], identity)
            self.assertIs(importer.return_value.extract.call_args.args[2]["acquisition"], identity)
            self.assertEqual(tagger.call_args.kwargs["policy"], policy)

    def test_unknown_serial_keeps_recovered_content_area_and_refuses_usb_join(self):
        identity = a.fallback("custom.E01", "E")
        common = {"image": "custom.E01", "exhibit": "E", "tool": "test", **a.provenance(identity)}
        ctx = {"common": common, "examined_at": 42, "acquisition": identity}
        stamp = datetime(2020, 1, 2, 3, 4, 6)
        found = {2: Directory(2, 0, [Entry("sample.txt", "SAMPLE.TXT", False, False, 3, 4, stamp, stamp)])}
        fs = NS(fatfs=NS(bpb=NS(BPB_RootEntCnt=0, BPB_BytsPerSec=512, BPB_SecPerClus=1,
                                BPB_RsvdSecCnt=1, BPB_NumFATs=1, BPB_TotSec32=8),
                        bpb_ext=NS(BPB_FATSz32=1)))
        image = bytearray(4096)
        image[1536:1540] = b"data"
        ev = Evidence()
        with patch.object(media, "carve_fat32", return_value=found), \
             patch("extractor.fatcarve.carve_fat32", return_value=found):
            media._recovered_entries(ev, io.BytesIO(image), fs, identity, ZoneInfo("UTC"), 42, common)
            content._recovered(ev, io.BytesIO(image), fs, ctx, identity)
        self.assertEqual(ev.problems, [])
        rows = {row[0]: row for row in ev.rows()}
        location = a.area(identity)
        self.assertEqual(rows["fileCreated"][4], location)
        self.assertEqual(json.loads(rows["fileContent"][5])["location"], location)
        self.assertEqual(rows["unallocatedOnDevice"][3], identity["device_identity"])
        ev.add("usbInsert", 1, 1, "USB-SERIAL", "")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "facts.json"
            ev.write_json(path, {})
            source = JsonFacts(path)
            ids = {f.kind: f.id for f in source.all()}
            certificate = check({"deviceExamined": [ids["usbInsert"], ids["unallocatedOnDevice"]]},
                                "NoUnknownUsbJoin", source, out_dir=Path(temp))
            self.assertEqual(certificate["status"], "rejected")
            supported = check({"recoveredOnDevice": [ids["fileCreated"], ids["unallocatedOnDevice"]]},
                              "KnownRecoveryArea", source, out_dir=Path(temp))
            self.assertEqual(supported["status"], "verified")
            self.assertEqual(supported["axioms"], [])


if __name__ == "__main__":
    unittest.main()
