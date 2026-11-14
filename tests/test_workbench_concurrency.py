"""One Workbench supports threaded API calls without duplicating evidence or IDs."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from agent.conclusions import Conclusions
from agent.tools import Workbench


class WorkbenchConcurrency(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        facts = self.root / "facts.json"
        facts.write_text(json.dumps({
            "strings": {"1": "fixture device", "2": "fixture volume"},
            "facts": [{"id": 1, "kind": "usbInsert", "t": 0, "res": 0,
                       "obj": 1, "aux": 2, "prov": {"artifact": "fixture"}}]}))
        self.run = self.root / "run"
        self.bench = Workbench(facts, self.run, "concurrency-test")
        self.addCleanup(self.bench._db.close)

    def fake_check(self, claim, finding_id, source, question, out_dir, proposer):
        """Fake only the proof execution; retain its certificate/log write contract."""
        time.sleep(0.015)  # Widen the ID-allocation race before the first write.
        row = {"claim": claim, "finding_id": finding_id, "status": "verified",
               "strength": "strong", "rules": [], "english": "A fixture observation.",
               "proposer": proposer}
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{finding_id}.json").write_text(json.dumps(row))
        with (out_dir / "proposals.jsonl").open("a") as stream:
            stream.write(json.dumps(row) + "\n")
        return row

    def test_worker_threads_read_shared_sql_and_facts_but_cannot_write(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            reads = [pool.submit(self.bench.sql, "SELECT id, obj FROM facts") for _ in range(16)]
            facts = [pool.submit(self.bench.fact, 1) for _ in range(16)]
            mutations = [pool.submit(self.bench.sql, query) for query in (
                "DELETE FROM facts", "DROP TABLE facts", "UPDATE facts SET obj = 'changed'",
                "ATTACH DATABASE 'external.db' AS external", "PRAGMA writable_schema = 1")]
            for read in reads:
                self.assertEqual(read.result(timeout=5)["rows"], [[1, "fixture device"]])
            for fact in facts:
                self.assertEqual(fact.result(timeout=5)["obj"], "fixture device")
            for mutation in mutations:
                self.assertIn("error", mutation.result(timeout=5))
        self.assertEqual(self.bench.sql("SELECT count(*) FROM facts")["rows"], [[1]])

    def test_query_budget_recovers_after_interruptions_in_worker_threads(self):
        expensive = ("WITH RECURSIVE numbers(n) AS (SELECT 1 UNION ALL "
                     "SELECT n + 1 FROM numbers WHERE n < 1000000) SELECT sum(n) FROM numbers")
        with patch("agent.tools.STEP_LIMIT", 10_000), ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(self.bench.sql, query) for query in
                       (expensive, "SELECT count(*) FROM facts", expensive, "SELECT id FROM facts")]
            results = [future.result(timeout=5) for future in futures]
        self.assertIn("interrupted", results[0]["error"])
        self.assertEqual(results[1]["rows"], [[1]])
        self.assertIn("interrupted", results[2]["error"])
        self.assertEqual(results[3]["rows"], [[1]])

    def test_concurrent_duplicate_and_distinct_claims_have_unique_saved_ids(self):
        proposals = [{"usbConnected": [i]} for i in range(1, 7)] * 4
        with patch("agent.tools.checker.check", side_effect=self.fake_check) as checker, \
             ThreadPoolExecutor(max_workers=12) as pool:
            futures = [pool.submit(self.bench.check, "Fixture question", claim) for claim in proposals]
            results = [future.result(timeout=5) for future in futures]
        rows = self.bench._log()
        self.assertEqual(checker.call_count, 6)
        self.assertEqual(len(rows), 6)
        self.assertEqual({row["finding_id"] for row in rows}, {f"A{i:03d}" for i in range(1, 7)})
        by_claim = {json.dumps(row["claim"]): row["finding_id"] for row in rows}
        for claim, result in zip(proposals, results):
            self.assertEqual(result["finding_id"], by_claim[json.dumps(claim)])
        self.assertEqual(sum("note" in result for result in results), 18)
        for row in rows:
            saved = json.loads((self.run / f"{row['finding_id']}.json").read_text())
            self.assertEqual(saved, row)

    def test_concurrent_conclusions_keep_unique_ids_and_duplicate_detection(self):
        with patch("agent.tools.checker.check", side_effect=self.fake_check):
            finding = self.bench.check("Fixture question", {"usbConnected": [1]})["finding_id"]
        original_all = Conclusions.all

        def slow_read(conclusions):
            rows = original_all(conclusions)
            time.sleep(0.015)  # Multiple unlocked callers would allocate the same ID.
            return rows

        texts = [f"The observation suggests {word}." for word in ("alpha", "beta", "gamma", "delta")] * 4
        with patch.object(Conclusions, "all", slow_read), ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(self.bench.conclude, text, [finding]) for text in texts]
            results = [future.result(timeout=5) for future in futures]
        rows = Conclusions(self.run).all()
        self.assertEqual(len(rows), 4)
        self.assertEqual({row["conclusion_id"] for row in rows}, {f"C{i:03d}" for i in range(1, 5)})
        by_text = {row["text"]: row["conclusion_id"] for row in rows}
        for text, result in zip(texts, results):
            self.assertEqual(result["status"], "accepted")
            self.assertEqual(result["conclusion_id"], by_text[text])
        self.assertEqual(self.bench.conclude("An unsupported inference.", ["A999"])["status"], "rejected")

    def test_conclusion_waits_for_a_complete_proposal_log_write(self):
        partial_written = threading.Event()
        finish_write = threading.Event()
        conclusion_started = threading.Event()
        conclusion_finished = threading.Event()

        def partial_check(claim, finding_id, source, question, out_dir, proposer):
            row = {"claim": claim, "finding_id": finding_id, "status": "verified",
                   "strength": "strong", "rules": [], "english": "A fixture observation."}
            out_dir.mkdir(parents=True, exist_ok=True)
            encoded = json.dumps(row)
            with (out_dir / "proposals.jsonl").open("a") as stream:
                stream.write(encoded[:len(encoded) // 2])
                stream.flush()
                partial_written.set()
                if not finish_write.wait(5):
                    raise TimeoutError("test did not release the proposal writer")
                stream.write(encoded[len(encoded) // 2:] + "\n")
            return row

        def conclude():
            conclusion_started.set()
            try:
                return self.bench.conclude("The observation suggests a connection.", ["A001"])
            finally:
                conclusion_finished.set()

        with patch("agent.tools.checker.check", side_effect=partial_check), ThreadPoolExecutor(max_workers=2) as pool:
            checking = pool.submit(self.bench.check, "Fixture question", {"usbConnected": [1]})
            try:
                self.assertTrue(partial_written.wait(5))
                concluding = pool.submit(conclude)
                self.assertTrue(conclusion_started.wait(5))
                self.assertFalse(conclusion_finished.wait(0.05))
            finally:
                finish_write.set()
            self.assertEqual(checking.result(timeout=5)["finding_id"], "A001")
            self.assertEqual(concluding.result(timeout=5)["status"], "accepted")
        self.assertEqual(len(self.bench._log()), 1)
        self.assertEqual(len(Conclusions(self.run).all()), 1)


if __name__ == "__main__":
    unittest.main()
