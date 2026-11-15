import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from extractor import image_integrity as image
from extractor.store import Evidence


class ImageIntegrity(unittest.TestCase):
    def test_complete_logical_stream_and_truncation(self):
        value = b"logical bytes not container bytes"
        got = image.hash_stream(io.BytesIO(value), len(value))
        self.assertEqual(got["md5"], hashlib.md5(value).hexdigest())
        self.assertEqual(got["sha256"], hashlib.sha256(value).hexdigest())
        for size in (len(value) - 1, len(value) + 1):
            with self.assertRaises(ValueError):
                image.hash_stream(io.BytesIO(value), size)

    def test_raw_has_no_invented_acquisition_match(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "case.raw"
            path.write_bytes(b"raw bytes")
            result = image.inspect(path)
            self.assertEqual(result["recorded"], [])
            self.assertEqual(result["comparisons"], [])
            ev = Evidence()
            image.extract(ev, path, {"common": {"image": "case.raw", "exhibit": "PC"}, "examined_at": 123})
            self.assertEqual(len(ev.rows()), 9)
            self.assertIn("no acquisition digest", ev.problems[0])

    def test_recorded_hash_does_not_replace_calculated_hash(self):
        value = b"logical bytes"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "case.E01"
            path.write_bytes(b"unused container")
            from contextlib import contextmanager
            @contextmanager
            def opened(_):
                yield io.BytesIO(value), len(value), [path], "ewf_logical_image"
            with patch.object(image, "logical_stream", opened), patch.object(image, "ewf_digests", return_value=[
                    ("md5", "0" * 32, "hash", 89), ("md5", hashlib.md5(value).hexdigest(), "digest", 100)]):
                result = image.inspect(path)
            self.assertEqual([entry["matches"] for entry in result["comparisons"]], [False, True])
            self.assertEqual(len(result["recorded"]), 2)


if __name__ == "__main__":
    unittest.main()
