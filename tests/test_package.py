"""External comparison inputs contain public questions, never expected answers."""
import json
from pathlib import Path
import tempfile
import unittest

from eval.package import prepare
from eval.submission import extract


class ComparisonPackage(unittest.TestCase):
    def setUp(self):
        self.public = {"schema_version": 2, "case_id": "unfamiliar-case",
                       "questions": [{"id": "Q", "prompt": "What is recorded?", "answer_schema": {"type": "string"}}]}

    def test_preparation_hashes_explicit_images_without_copying_private_siblings(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "questions.json").write_text(json.dumps(self.public))
            (root / "private-key.json").write_text('{"expected":"SECRET"}')
            (root / "disk.E01").write_bytes(b"evidence bytes")
            out = root / "package"
            result = prepare(root / "questions.json", [root / "disk.E01"], out)
            self.assertEqual(result["status"], "prepared_not_finalized_not_run")
            self.assertFalse(result["model_invoked"])
            self.assertEqual(result["evidence"][0]["bytes"], 14)
            self.assertEqual({p.name for p in out.iterdir()},
                             {"manifest.json", "questions.json", "answers.template.json", "MULDER.md"})
            self.assertNotIn("SECRET", (out / "MULDER.md").read_text())
            with self.assertRaises(FileExistsError):
                prepare(root / "questions.json", [root / "disk.E01"], out)

    def test_private_question_profile_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.public["questions"][0]["expected"] = "secret"
            path = root / "private.json"
            path.write_text(json.dumps(self.public))
            with self.assertRaises(ValueError):
                prepare(path, [], root / "out")
            self.assertFalse((root / "out").exists())

    def test_typed_block_is_preserved_and_prose_is_never_judged(self):
        answer = {"schema_version": 2, "case_id": "unfamiliar-case",
                  "answers": [{"question_id": "Q", "status": "answered", "answer": False}]}
        block = "```json\n" + json.dumps(answer) + "\n```\n"
        self.assertEqual(extract("Report text.\n" + block, self.public), answer)
        for bad in ("The answer is false.", block + block,
                    block.replace("unfamiliar-case", "wrong-case"),
                    block.replace('"Q"', '"different-question"')):
            with self.assertRaises(ValueError):
                extract(bad, self.public)


if __name__ == "__main__":
    unittest.main()
