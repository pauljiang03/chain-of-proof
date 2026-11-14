"""The investigator's tools: read-only access, and proposals that go through the kernel."""
import json
import tempfile
import unittest
from pathlib import Path

from agent.tools import FORMS, Workbench
from agent import mcp_server
from checker import claims

ROOT = Path(__file__).resolve().parent.parent
FACTS = ROOT / "evidence" / "case_facts.json"
ROWS = json.loads(FACTS.read_text())["_meta"]["facts"]


class Tools(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.bench = Workbench(FACTS, self.tmp.name, "test")

    def tearDown(self):
        self.tmp.cleanup()

    def test_every_approved_set_is_described_to_the_investigator(self):
        self.assertEqual(set(FORMS), set(claims.SETS))

    def test_sql_reads_but_cannot_write_or_reach_files(self):
        self.assertEqual(self.bench.sql("SELECT count(*) FROM facts")["rows"][0][0], ROWS)
        for bad in ("DELETE FROM facts", "DROP TABLE facts", "ATTACH DATABASE 'x.db' AS x",
                    "UPDATE facts SET obj = 'x'", "PRAGMA writable_schema = 1",
                    "SELECT readfile('/etc/passwd')", "SELECT 1; SELECT 2"):
            self.assertIn("error", self.bench.sql(bad), bad)
        self.assertEqual(self.bench.sql("SELECT count(*) FROM facts")["rows"][0][0], ROWS)

    def test_a_wrong_proposal_is_refused_with_the_values_that_disagree(self):
        zip_open = self.bench.sql("SELECT id FROM facts WHERE kind='lnkTarget' AND aux='9E6A5B82'")["rows"][0][0]
        rm1 = self.bench.sql("SELECT id FROM facts WHERE kind='volumeOnDevice' AND aux='5C754D3E'")["rows"][0][0]
        r = self.bench.check("Was the zip opened from RM#1?", {"openedFromDevice": [zip_open, rm1]})
        self.assertEqual(r["status"], "rejected")
        self.assertIn("9E6A5B82", r["failing_checks"][0])
        self.assertIn("5C754D3E", r["failing_checks"][0])
        again = self.bench.check("same again", {"openedFromDevice": [zip_open, rm1]})
        self.assertIn("already proposed", again["note"])      # logged once, not twice
        self.assertEqual(len((Path(self.tmp.name) / "proposals.jsonl").read_text().splitlines()), 1)

    def test_a_supported_proposal_is_certified_and_logged_with_its_proposer(self):
        usb = self.bench.sql("SELECT id FROM facts WHERE kind='usbInsert' ORDER BY id")["rows"][0][0]
        r = self.bench.check("Which devices?", json.dumps({"usbConnected": [usb]}))
        self.assertEqual(r["status"], "verified")
        cert = json.loads((Path(self.tmp.name) / f"{r['finding_id']}.json").read_text())
        self.assertEqual(cert["proposer"], "test")
        self.assertEqual(cert["english"], r["sentence"])

    def test_mcp_server_offers_exactly_the_four_tools(self):
        self.assertEqual([t["name"] for t in mcp_server.TOOLS], ["forms", "sql", "fact", "check"])
        out = mcp_server.call(self.bench, "sql", {"query": "SELECT count(*) FROM facts"})
        self.assertEqual(out.splitlines()[1], f"[{ROWS}]")


class Audit(unittest.TestCase):
    """The with/without-checker comparison: a verdict counts only with a certificate."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.bench = Workbench(FACTS, self.tmp.name, "test")

    def tearDown(self):
        self.tmp.cleanup()

    def test_report_sentences_are_parsed_by_number(self):
        from agent.audit import parse_statements
        report = "Intro\nF1: one thing\n**F2:** another\n- not a finding\nF3. third\nF1: repeat"
        self.assertEqual(parse_statements(report), [(1, "one thing"), (2, "another"), (3, "third")])

    def test_the_report_writer_gets_no_checker(self):
        from agent.brief import REPORT_BRIEF
        self.assertEqual([t["name"] for t in mcp_server.tools_for(["sql", "fact"])], ["sql", "fact"])
        self.assertNotIn("check(", REPORT_BRIEF)

    def test_a_verdict_without_a_certificate_does_not_count(self):
        from agent.audit import merge
        usb = self.bench.sql("SELECT id FROM facts WHERE kind='usbInsert' ORDER BY id")["rows"][0][0]
        real = self.bench.check("q", {"usbConnected": [usb]})["finding_id"]
        for row in ({"statement": 1, "verdict": "certified", "finding_ids": [real], "reason": "same"},
                    {"statement": 2, "verdict": "certified", "finding_ids": ["A999"], "reason": "made up"},
                    {"statement": 3, "verdict": "weaker", "finding_ids": [], "reason": "nothing cited"},
                    {"statement": 4, "verdict": "no_records", "reason": "none"}):
            self.assertIn("recorded", mcp_server.call(self.bench, "record", row))
        self.assertIn("must be one of", mcp_server.call(
            self.bench, "record", {"statement": 5, "verdict": "true", "reason": ""}))
        out = merge(Path(self.tmp.name), [(n, f"s{n}") for n in range(1, 6)])
        got = {r["statement"]: r["verdict"] for r in out["statements"]}
        self.assertEqual(got, {1: "certified", 2: "refused", 3: "refused",
                               4: "no_records", 5: "not_audited"})
        self.assertEqual(out["statements"][0]["findings"][0]["finding_id"], real)


if __name__ == "__main__":
    unittest.main()
