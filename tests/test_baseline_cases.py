"""Baseline isolation and non-destructive output setup, without kernel batches."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent.case import LEGACY_PROFILE
from eval import baseline


class BaselineCases(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.facts = self.write("facts.json", {
            "_meta": {"case": "Independent Case", "pc": {"time_zone": "America/Los_Angeles"}},
            "facts": [], "strings": {},
        })
        self.reference = self.write("reference.json", {
            "source": "Independent Case", "tolerance_s": 1,
            "time_zone": "America/Los_Angeles", "items": [],
        })
        self.labels = self.write("labels.json", {
            "facts": {}, "claims": [
                {"id": "true-custom", "label": True, "claim": {}},
                {"id": "false-custom", "label": False, "claim": {}},
            ],
        })
        self.certs, self.run, self.output = (self.root / name for name in ("certs", "run.json", "results.json"))
        self.argv = ["--facts", str(self.facts), "--certs", str(self.certs),
                     "--run", str(self.run), "--out", str(self.output)]

    def write(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value))
        return path

    def invoke(self, extra=()):
        with patch.object(baseline.miner, "mine", return_value=[]) as miner, \
             patch.object(baseline.scorer, "score_gate", return_value=[]) as gate, \
             patch.object(baseline.scorer, "main", return_value=0) as score, \
             contextlib.redirect_stdout(io.StringIO()):
            result = baseline.main(self.argv + list(extra))
        return result, miner, gate, score

    def test_custom_facts_require_reference_before_any_mining_or_output(self):
        with patch.object(baseline.miner, "mine") as miner, \
             contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            baseline.main(self.argv)
        miner.assert_not_called()
        for path in (self.certs, self.run, self.output):
            self.assertFalse(path.exists())

    def test_custom_reference_uses_its_name_and_never_injects_nist_probes(self):
        result, miner, gate, score = self.invoke(["--reference", str(self.reference), "--complete"])
        self.assertEqual(result, 0)
        self.assertTrue(miner.call_args.kwargs["complete"])
        gate.assert_not_called()
        self.assertIn("--no-gate", score.call_args.args[0])
        document = json.loads(self.run.read_text())
        self.assertEqual(document["case"]["name"], "Independent Case")
        self.assertEqual(document["case"]["time_zone"], "America/Los_Angeles")
        self.assertTrue(document["case"]["mining"]["complete"])

    def test_explicit_probes_include_only_false_claims_and_use_reference_zone(self):
        _, _, gate, score = self.invoke(["--reference", str(self.reference),
                                         "--labeled-claims", str(self.labels)])
        probes = gate.call_args.args[0]["claims"]
        self.assertEqual([p["label"] for p in probes], [False])
        self.assertEqual(probes[0]["id"], "P001")
        self.assertEqual(gate.call_args.kwargs["time_zone"], "America/Los_Angeles")
        argv = score.call_args.args[0]
        self.assertEqual(argv[argv.index("--labeled-claims") + 1], str(self.labels))

    def test_original_profile_retains_default_reference_and_false_probes(self):
        data = json.loads(self.reference.read_text())
        data["source"] = "NIST CFReDS Data Leakage Case, legacy"
        self.reference.write_text(json.dumps(data))
        labels = json.loads(self.labels.read_text())
        labels["claims"][1]["id"] = "F99"
        self.labels.write_text(json.dumps(labels))
        with patch.object(baseline, "select_case", return_value=(LEGACY_PROFILE, "legacy")), \
             patch.object(baseline.scorer, "REFERENCE", self.reference), \
             patch.object(baseline.scorer, "LABELED", self.labels):
            _, _, gate, _ = self.invoke()
        self.assertEqual(gate.call_args.args[0]["claims"][0]["id"], "P99")
        self.assertEqual(json.loads(self.run.read_text())["case"]["name"], LEGACY_PROFILE.name)

    def test_existing_outputs_and_aliases_are_refused_without_modifying_them(self):
        self.certs.mkdir()
        sentinel = self.certs / "original-proof.lean"
        sentinel.write_text("preserve the previous certificate")
        with patch.object(baseline.miner, "mine") as miner, \
             contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            baseline.main(self.argv + ["--reference", str(self.reference)])
        miner.assert_not_called()
        self.assertEqual(sentinel.read_text(), "preserve the previous certificate")
        sentinel.unlink()
        self.certs.rmdir()
        for path in (self.certs, self.run, self.output):
            with self.subTest(path=path):
                path.write_text("keep original")
                with patch.object(baseline.miner, "mine") as miner, \
                     contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    baseline.main(self.argv + ["--reference", str(self.reference)])
                miner.assert_not_called()
                self.assertEqual(path.read_text(), "keep original")
                path.unlink()
        with patch.object(baseline.miner, "mine") as miner, \
             contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            baseline.main(self.argv + ["--reference", str(self.reference), "--out", str(self.run)])
        miner.assert_not_called()
        self.assertFalse(self.run.exists())


if __name__ == '__main__':
    unittest.main()
