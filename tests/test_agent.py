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


class Tools(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.bench = Workbench(FACTS, self.tmp.name, "test")

    def tearDown(self):
        self.tmp.cleanup()

    def test_every_approved_set_is_described_to_the_investigator(self):
        self.assertEqual(set(FORMS), set(claims.SETS))

    def test_sql_reads_but_cannot_write_or_reach_files(self):
        self.assertEqual(self.bench.sql("SELECT count(*) FROM facts")["rows"][0][0], 242)
        for bad in ("DELETE FROM facts", "DROP TABLE facts", "ATTACH DATABASE 'x.db' AS x",
                    "UPDATE facts SET obj = 'x'", "PRAGMA writable_schema = 1",
                    "SELECT readfile('/etc/passwd')", "SELECT 1; SELECT 2"):
            self.assertIn("error", self.bench.sql(bad), bad)
        self.assertEqual(self.bench.sql("SELECT count(*) FROM facts")["rows"][0][0], 242)

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
        self.assertEqual(out.splitlines()[1], "[242]")


if __name__ == "__main__":
    unittest.main()
