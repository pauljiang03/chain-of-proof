import tempfile
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from extractor import antivirus as av


class Antivirus(unittest.TestCase):
    def test_hits_bind_only_staged_files_and_limit_hit_is_not_malware(self):
        mapping = {"/tmp/1.bin": {"path": "C:/record.exe", "sha256": "hash"}}
        result = av.parse_results("/tmp/1.bin: Example.Signature FOUND\n/other: Fiction FOUND", mapping, 1)
        self.assertEqual(result["detections"][0]["path"], "C:/record.exe")
        self.assertEqual(len(result["detections"]), 1)
        self.assertEqual(len(result["errors"]), 1)
        result = av.parse_results("/tmp/1.bin: Heuristics.Limits.Exceeded.MaxFileSize FOUND", mapping, 1)
        self.assertEqual(result["detections"], [])
        self.assertTrue(result["errors"])
        self.assertEqual(len(result["limit_hits"]), 1)

    def test_scanner_failure_is_not_a_negative_result(self):
        self.assertTrue(av.parse_results("", {}, 2)["errors"])
        self.assertTrue(av.parse_results("", {}, 1)["errors"])
        self.assertTrue(av.parse_results("WARNING: skipped file", {}, 0)["errors"])
        self.assertFalse(av.parse_results("", {}, 0)["errors"])

    def test_copy_enforces_recorded_size_and_nonexecutable_mode(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, destination = root / "source", root / "staged"
            source.write_bytes(b"bytes")
            class FilesystemInt64(int):
                pass
            self.assertEqual(len(av.copy_file(source, destination, FilesystemInt64(5))), 64)
            self.assertEqual(destination.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(ValueError):
                av.copy_file(source, root / "short", 4)
            with self.assertRaises(ValueError):
                av.copy_file(source, root / "long", 6)

    def test_timeout_retains_positive_observations_without_claiming_complete_scan(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "fixture.ndb").write_text("test database identity only")
            source = root / "evidence"
            source.write_bytes(b"fixture bytes")
            def command(args, **options):
                if args[1] == "--version":
                    return subprocess.CompletedProcess(args, 0, "ClamAV fixture")
                staged = str(Path(args[-1]) / "00000000.bin")
                options["stdout"].write((staged + ": Example.Signature FOUND\n").encode())
                raise subprocess.TimeoutExpired(args, av.TIMEOUT)
            with patch.object(av, "candidates", return_value=iter([source])), patch.object(av.subprocess, "run", command):
                result = av.scan(object(), executable="fixture-scanner", database=root)
            self.assertFalse(result["complete_allocated_scope"])
            self.assertEqual(result["exit_code"], 124)
            self.assertEqual(result["detections"][0]["path"], str(source))
            self.assertTrue(any("time limit" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
