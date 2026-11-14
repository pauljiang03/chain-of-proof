"""An investigation manifest binds actual bytes without inventing model provenance."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent import run_manifest


class RunManifest(unittest.TestCase):
    def test_binds_input_and_working_source_bytes_and_marks_unknown_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = root / "run"
            run.mkdir()
            (root / "agent").mkdir()
            code = root / "agent" / "local.py"
            code.write_text("value = 3\n")
            facts = root / "facts.json"
            facts.write_bytes(b'{"facts":[]}\n')
            (run / "case-profile.json").write_text('{"name":"Public"}')
            (run / "prompt.md").write_text("Use the supplied records.")
            # A sibling reference is deliberately never an input to create().
            (root / "reference.json").write_text("PRIVATE-REFERENCE-CONTENT")
            with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "SECRET-PROVIDER-KEY"}):
                value = run_manifest.create(run, facts=facts, backend="deepagents", model="alias",
                                            minutes=1, root=root)
            self.assertEqual(value["inputs"]["facts"]["sha256"], hashlib.sha256(facts.read_bytes()).hexdigest())
            self.assertEqual(value["software"]["source_sha256"]["agent/local.py"],
                             hashlib.sha256(code.read_bytes()).hexdigest())
            self.assertIsNone(value["software"]["git"]["commit"])
            self.assertEqual(value["investigator"]["resolved_model_status"], "not_observed")
            self.assertIsNone(value["investigator"]["resolved_model"])
            text = (run / "run-manifest.json").read_text()
            self.assertNotIn("PRIVATE-REFERENCE-CONTENT", text)
            self.assertNotIn("SECRET-PROVIDER-KEY", text)
            self.assertNotIn("reference.json", text)
            self.assertEqual(json.loads(text), value)
            with self.assertRaises(FileExistsError):
                run_manifest.create(run, facts=facts, backend="deepagents", model="other",
                                    minutes=1, root=root)
            self.assertEqual((run / "run-manifest.json").read_text(), text)

    def test_file_binding_streams_large_inputs_and_changes_with_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "facts.bin"
            data = b"a" * (2 * 1024 * 1024 + 1)
            path.write_bytes(data)
            with patch.object(Path, "read_bytes", side_effect=AssertionError("do not load whole file")):
                first = run_manifest.file_binding(path)
            self.assertEqual(first["sha256"], hashlib.sha256(data).hexdigest())
            self.assertEqual(first["bytes"], len(data))
            with path.open("ab") as stream:
                stream.write(b"!")
            self.assertNotEqual(first["sha256"], run_manifest.file_binding(path)["sha256"])
