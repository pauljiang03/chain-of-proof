"""One tool audit for both backends; integrity is separate from authenticity."""
import hashlib
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from agent.audit import AuditError, verify_audit
from agent.tools import Workbench


def digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=True, allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


class ToolAudit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.facts = self.root / "facts.json"
        self.facts.write_text(json.dumps({
            "strings": {"1": "DEVICE", "2": "PC"},
            "facts": [{"id": 1, "kind": "usbInsert", "t": 0, "res": 0,
                       "obj": 1, "aux": 2, "prov": {"artifact": "test"}}]}))
        self.run = self.root / "run"
        self.bench = Workbench(self.facts, self.run, "test")
        self.path = self.run / "audit.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def events(self):
        return [json.loads(line) for line in self.path.read_text().splitlines()]

    def fake_check(self, claim, finding_id, source, question, run_dir, proposer):
        # A stub isolates audit behavior; real kernel behavior has its own tests.
        result = {"status": "verified", "finding_id": finding_id,
                  "strength": "direct", "rules": [], "english": "A device is recorded.",
                  "claim": claim, "question": question, "proposer": proposer}
        with (Path(run_dir) / "proposals.jsonl").open("a") as stream:
            stream.write(json.dumps(result) + "\n")
        return result

    def test_all_five_tools_record_exact_arguments_results_and_finding_link(self):
        with patch("agent.tools.checker.check", side_effect=self.fake_check):
            results = [self.bench.forms(), self.bench.sql("SELECT id FROM facts"),
                       self.bench.fact(fact_id=1),
                       self.bench.check("Which device?", {"usbConnected": [1]}),
                       self.bench.conclude("Evidence supports this conclusion.", ["A001"])]
        events = self.events()
        self.assertEqual([e["tool"] for e in events], ["forms", "sql", "fact", "check", "conclude"])
        self.assertEqual([e["result"] for e in events], results)
        self.assertEqual(events[0]["arguments"], {})
        self.assertEqual(events[2]["arguments"], {"fact_id": 1})
        self.assertEqual(events[3]["arguments"], {
            "question": "Which device?", "claim": {"usbConnected": [1]}})
        self.assertEqual(events[3]["finding_id"], "A001")
        self.assertEqual(events[4]["result"]["strength"], "judgment")
        self.assertEqual(events[0]["previous_sha256"], None)
        for earlier, later in zip(events, events[1:]):
            self.assertEqual(later["previous_sha256"], earlier["event_sha256"])
        for event in events:
            self.assertEqual(event["result_sha256"], digest(event["result"]))
            self.assertGreaterEqual(event["duration_ns"], 0)
            self.assertTrue(event["started_at"].endswith("Z"))
            self.assertTrue(event["completed_at"].endswith("Z"))
            self.assertTrue(event["success"])
        state = verify_audit(self.path)
        self.assertTrue(state["passed"], state)
        self.assertEqual(state["count"], 5)
        self.assertEqual(state["head"], events[-1]["event_sha256"])

    def test_duplicate_checks_are_separate_calls_but_share_original_finding(self):
        with patch("agent.tools.checker.check", side_effect=self.fake_check) as checker:
            first = self.bench.check("First question", {"usbConnected": [1]})
            second = self.bench.check("Second question", {"usbConnected": [1]})
        self.assertEqual(checker.call_count, 1)
        self.assertEqual(first["finding_id"], second["finding_id"])
        self.assertIn("already proposed", second["note"])
        events = self.events()
        self.assertEqual(len(events), 2)
        self.assertNotEqual(events[0]["call_id"], events[1]["call_id"])
        self.assertEqual(events[1]["arguments"]["question"], "Second question")
        self.assertEqual(len((self.run / "proposals.jsonl").read_text().splitlines()), 1)
        self.assertTrue(verify_audit(self.path)["passed"])

    def test_denied_sql_missing_record_and_invalid_json_are_logged(self):
        results = [self.bench.sql("DELETE FROM facts"), self.bench.fact(999),
                   self.bench.check("Bad JSON", "{broken"), self.bench.conclude("", [])]
        events = self.events()
        self.assertEqual([event["result"] for event in events], results)
        self.assertEqual([event["outcome"] for event in events],
                         ["error", "error", "rejected", "rejected"])
        self.assertTrue(all(not event["success"] for event in events))
        self.assertEqual(events[2]["arguments"]["claim"], "{broken")
        self.assertEqual(results[2]["proof_gap"]["status"], "diagnostic")
        self.assertEqual(results[2]["proof_gap"]["requirements"][0]["category"], "malformed_claim")
        self.assertTrue(verify_audit(self.path)["passed"])

    def test_checker_proof_gap_passes_through_without_becoming_a_finding(self):
        diagnostic = {"status": "diagnostic", "summary": "need an actual record"}
        result = {"status": "rejected", "finding_id": "A001", "reason": "missing",
                  "proof_gap": diagnostic}
        with patch("agent.tools.checker.check", return_value=result):
            returned = self.bench.check("A question", {"usbConnected": [99]})
        self.assertEqual(returned["status"], "rejected")
        self.assertIs(returned["proof_gap"], diagnostic)
        self.assertEqual(self.events()[0]["result"], returned)

    def test_uncaught_exception_records_only_class_and_reraises_original(self):
        secret = "exception-secret-must-not-be-collected"
        with patch.dict("os.environ", {"AUDIT_TEST_SECRET": "environment-secret-not-collected"}):
            with patch.object(self.bench.source, "get", side_effect=RuntimeError(secret)):
                with self.assertRaisesRegex(RuntimeError, secret):
                    self.bench.fact(1)
        event = self.events()[0]
        self.assertEqual(event["error"], {"type": "RuntimeError"})
        self.assertEqual(event["outcome"], "error")
        self.assertIsNone(event["result"])
        self.assertNotIn(secret, self.path.read_text())
        self.assertNotIn("environment-secret-not-collected", self.path.read_text())
        self.assertTrue(verify_audit(self.path)["passed"])

    def test_malformed_python_invocation_is_logged_without_error_message(self):
        with self.assertRaises(TypeError):
            self.bench.fact()
        event = self.events()[0]
        self.assertEqual(event["error"], {"type": "TypeError"})
        self.assertEqual(event["arguments"], {"positional": [], "keyword": {}})

    def test_non_json_sql_results_log_sanitized_failures_and_keep_chain_valid(self):
        cases = [("SELECT 1e999 AS n", ValueError),
                 ("SELECT x'41' AS blob", TypeError)]
        for index, (query, error_type) in enumerate(cases, 1):
            with self.subTest(query=query):
                with self.assertRaises(error_type) as raised:
                    self.bench.sql(query)
                events = self.events()
                self.assertEqual(len(events), index)
                event = events[-1]
                self.assertEqual(event["arguments"], {"query": query})
                self.assertEqual(event["error"], {"type": error_type.__name__})
                self.assertEqual(event["outcome"], "error")
                self.assertFalse(event["success"])
                self.assertIsNone(event["result"])
                self.assertNotIn(str(raised.exception), self.path.read_text())
                state = verify_audit(self.path)
                self.assertTrue(state["passed"], state)
                self.assertEqual(state["count"], index)
        self.assertEqual(self.bench.sql("SELECT id FROM facts")["rows"], [[1]])
        self.assertEqual(verify_audit(self.path)["count"], 3)
        self.assertTrue(verify_audit(self.path)["passed"])

    def test_concurrent_calls_keep_sequential_unique_events_and_correct_results(self):
        def work(index):
            if index % 2:
                return self.bench.fact(1)["id"]
            return self.bench.sql("SELECT id FROM facts")["rows"][0][0]
        with ThreadPoolExecutor(max_workers=8) as executor:
            self.assertEqual(list(executor.map(work, range(40))), [1] * 40)
        events = self.events()
        self.assertEqual([event["sequence"] for event in events], list(range(1, 41)))
        self.assertEqual(len({event["call_id"] for event in events}), 40)
        self.assertTrue(verify_audit(self.path)["passed"])

    def test_reopening_appends_and_preserves_original_bytes(self):
        self.bench.fact(1)
        first = self.path.read_bytes()
        reopened = Workbench(self.facts, self.run)
        reopened.forms()
        self.assertTrue(self.path.read_bytes().startswith(first))
        self.assertEqual([e["sequence"] for e in self.events()], [1, 2])
        self.assertTrue(verify_audit(self.path)["passed"])

    def test_extraction_metadata_is_written_once_without_source_reload_or_overwrite(self):
        metadata = {"facts": 1, "by_kind": {"usbInsert": 1}, "unparsed": []}
        self.bench.source.metadata = metadata
        run = self.root / "metadata-run"
        with patch("agent.tools.open_source", return_value=self.bench.source):
            Workbench(self.facts, run)
            path = run / "extraction-metadata.json"
            self.assertEqual(json.loads(path.read_text()), metadata)
            original = path.read_bytes()
            self.bench.source.metadata = {"facts": 999}
            Workbench(self.facts, run)
            self.assertEqual(path.read_bytes(), original)

    def test_tampering_is_detected_and_never_truncated_or_repaired(self):
        self.bench.fact(1)
        event = self.events()[0]
        event["result"]["obj"] = "ALTERED"
        self.path.write_text(json.dumps(event) + "\n")
        damaged = self.path.read_bytes()
        state = verify_audit(self.path)
        self.assertFalse(state["passed"])
        self.assertIn("line 1: result digest mismatch", state["problems"])
        with self.assertRaises(AuditError):
            self.bench.fact(1)
        with self.assertRaises(AuditError):
            Workbench(self.facts, self.run)
        self.assertEqual(self.path.read_bytes(), damaged)

    def test_partial_or_malformed_events_fail_readonly_verification(self):
        self.bench.fact(1)
        good = self.path.read_bytes()
        for suffix in (b'{"unterminated":', b'not-json\n', b'\n', b'{"x":1,"x":2}\n'):
            with self.subTest(suffix=suffix):
                content = good + suffix
                self.path.write_bytes(content)
                state = verify_audit(self.path)
                self.assertFalse(state["passed"])
                self.assertEqual(self.path.read_bytes(), content)
                with self.assertRaises(AuditError):
                    self.bench.forms()
                self.assertEqual(self.path.read_bytes(), content)

    def test_external_head_detects_complete_rewrite_and_tail_removal(self):
        self.bench.fact(1)
        self.bench.forms()
        original = self.events()
        original_head = verify_audit(self.path)["head"]
        self.path.write_text(json.dumps(original[0]) + "\n")
        self.assertTrue(verify_audit(self.path)["passed"])
        self.assertFalse(verify_audit(self.path, original_head)["passed"])
        rewritten = original[0]
        rewritten["result"]["obj"] = "REWRITTEN"
        rewritten["result_sha256"] = digest(rewritten["result"])
        rewritten["event_sha256"] = digest({k: v for k, v in rewritten.items() if k != "event_sha256"})
        self.path.write_text(json.dumps(rewritten) + "\n")
        self.assertTrue(verify_audit(self.path)["passed"])
        self.assertFalse(verify_audit(self.path, original_head)["passed"])

    def test_missing_empty_and_unclosed_logs_have_explicit_results(self):
        self.assertFalse(verify_audit(self.root / "missing.jsonl")["passed"])
        self.assertEqual(verify_audit(self.path)["count"], 0)
        self.assertTrue(verify_audit(self.path)["passed"])
        self.bench.fact(1)
        self.path.write_bytes(self.path.read_bytes().removesuffix(b"\n"))
        self.assertFalse(verify_audit(self.path)["passed"])


if __name__ == "__main__":
    unittest.main()
