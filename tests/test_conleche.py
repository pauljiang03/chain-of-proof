"""The con-leche recheck accepts real certificates and nothing else."""
import json
import tempfile
import unittest
from pathlib import Path

from verifier import conleche

ROOT = Path(__file__).resolve().parent.parent

try:
    TOOLS = conleche.Toolchain()
except conleche.Unavailable as missing:
    TOOLS, WHY = None, str(missing)
else:
    WHY = ""


@unittest.skipUnless(TOOLS, f"con-leche is not available: {WHY}")
class ConLeche(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        run = json.loads((ROOT / "app" / "sample" / "run.json").read_text())
        cls.bundle = run
        cls.lean = next(f["lean"] for f in run["findings"] if f["finding_id"] == "A002")

    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.dir = Path(scratch.name)

    def test_accepts_a_real_certificate(self):
        result = conleche.check(self.lean, TOOLS, self.dir)
        self.assertTrue(result["accepted"], result["detail"])

    def test_rejects_an_export_changed_after_lean_accepted_it(self):
        # A002 claims the stick was connected before the file was opened. Move the
        # connection to a later time inside the exported proof: the claim is now false.
        export = conleche.export(self.lean, self.dir, TOOLS)
        text = export.read_text()
        self.assertEqual(text.count('"natVal":"1427119200000000"'), 1)
        export.write_text(text.replace('"natVal":"1427119200000000"', '"natVal":"1527119200000000"'))
        result = conleche.check_export(export, "Cert.A002.verified", TOOLS)
        self.assertFalse(result["accepted"])
        self.assertIn("Cert.A002.verified", result["detail"])

    def test_an_export_without_the_theorem_is_not_accepted(self):
        # con-leche exits 0 on an export that declares nothing.
        export = conleche.export(self.lean, self.dir, TOOLS)
        export.write_text(export.read_text().splitlines()[0] + "\n")
        result = conleche.check_export(export, "Cert.A002.verified", TOOLS)
        self.assertFalse(result["accepted"])
        self.assertIn("does not declare", result["detail"])

    def test_a_false_certificate_never_reaches_the_export(self):
        false_claim = self.lean.replace("1427119200000000", "1527119200000000")
        result = conleche.check(false_claim, TOOLS, self.dir)
        self.assertFalse(result["accepted"])
        self.assertIn("Lean did not accept", result["detail"])

    def test_checks_every_certificate_in_a_run(self):
        result = conleche.check_run(self.bundle, TOOLS, jobs=2)
        self.assertEqual(result["certificates"], len(self.bundle["findings"]))
        self.assertEqual(result["accepted"], result["certificates"], result["not_accepted"])
        self.assertEqual(result["checker"], "con-leche")

    def test_theorem_name_needs_exactly_one_namespace(self):
        self.assertEqual(conleche.theorem_name(self.lean), "Cert.A002.verified")
        with self.assertRaises(ValueError):
            conleche.theorem_name("theorem verified : True := trivial")


if __name__ == "__main__":
    unittest.main()
