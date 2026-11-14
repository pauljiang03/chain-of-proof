import copy
import tempfile
import unittest
from pathlib import Path

from eval.key_audit import audit, digest, timestamp_conversion


class KeyAudit(unittest.TestCase):
    def test_source_binding_and_literal_do_not_claim_semantic_proof(self):
        raw = b"Question\nExample value\n"
        reference = {"source_document": {"sha256": digest(raw)},
                     "review_status": "draft_requires_independent_review",
                     "questions": [{"id": "Q1", "expected": {"value": "Example value"},
                                    "source": {"start_line": 1, "end_line": 2, "sha256": digest(raw)},
                                    "field_sources": [{"pointer": "/value", "literal": "Example value",
                                                       "start_line": 2, "end_line": 2}]}]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.txt"
            path.write_bytes(raw)
            result = audit(reference, path)
            self.assertTrue(result["source_binding_passed"])
            self.assertEqual(result["semantic_correctness"], "not_proved")
            self.assertEqual(result["questions"][0]["literally_or_arithmetically_bound_leaves"], 1)
            altered = copy.deepcopy(reference)
            altered["questions"][0]["expected"]["value"] = "A guessed value"
            self.assertFalse(audit(altered, path)["source_binding_passed"])
            path.write_bytes(raw.replace(b"Example", b"Changed"))
            self.assertFalse(audit(reference, path)["source_binding_passed"])

    def test_timestamp_arithmetic_and_dst_do_not_guess(self):
        conversion = {"source_value": "2020-07-01T12:00:00", "source_timezone": "America/New_York"}
        timestamp_conversion(conversion, "2020-07-01T16:00:00Z")
        with self.assertRaisesRegex(ValueError, "does not equal"):
            timestamp_conversion(conversion, "2020-07-01T17:00:00Z")
        conversion["source_value"] = "2020-11-01T01:30:00"
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            timestamp_conversion(conversion, "2020-11-01T05:30:00Z")
        conversion["fold"] = 1
        timestamp_conversion(conversion, "2020-11-01T06:30:00Z")
        conversion["source_value"] = "2020-03-08T02:30:00"
        with self.assertRaisesRegex(ValueError, "does not exist"):
            timestamp_conversion(conversion, "2020-03-08T07:30:00Z")
