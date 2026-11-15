"""The con-leche recheck accepts real certificates and nothing else."""
import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import patch

from verifier import conleche
from checker.check import check
from checker.facts import JsonFacts
from extractor.store import Evidence

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
        # The frontend demo can change independently of these tampering checks.
        # Make the exact temporal premise under test explicit and stable.
        scratch = tempfile.TemporaryDirectory()
        cls.addClassCleanup(scratch.cleanup)
        directory = Path(scratch.name)
        evidence = Evidence()
        evidence.add('usbInsert', 1427119200000000, 1, 'fixture-device')
        evidence.add('lnkTarget', 1427119201000000, 1, 'fixture-target', 'fixture-volume')
        evidence.write_json(directory / 'facts.json', {})
        source = JsonFacts(directory / 'facts.json')
        ids = {fact.kind: fact.id for fact in source.all()}
        certificate = check({'before': [ids['usbInsert'], ids['lnkTarget']]},
                            'ConLecheFixture', source, out_dir=directory)
        if certificate['status'] != 'verified':
            raise AssertionError(certificate)
        cls.lean = (directory / certificate['lean_file']).read_text()
        cls.theorem = 'Cert.ConLecheFixture.verified'
        cls.source = source
        cls.facts_path = directory / 'facts.json'
        cls.certificate = dict(certificate, lean=cls.lean)
        cls.bundle = {'findings': [cls.certificate]}

    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.dir = Path(scratch.name)

    def test_accepts_a_real_certificate(self):
        result = conleche.check(self.lean, TOOLS, self.dir)
        self.assertTrue(result["accepted"], result["detail"])

    def test_rejects_an_export_changed_after_lean_accepted_it(self):
        # Move the earlier source timestamp past the later timestamp. The formal
        # ordering claim is now false, without asserting physical actions occurred.
        export = conleche.export(self.lean, self.dir, TOOLS)
        text = export.read_text()
        self.assertEqual(text.count('"natVal":"1427119200000000"'), 1)
        export.write_text(text.replace('"natVal":"1427119200000000"', '"natVal":"1527119200000000"'))
        result = conleche.check_export(export, self.theorem, TOOLS)
        self.assertFalse(result["accepted"])
        self.assertIn(self.theorem, result["detail"])

    def test_an_export_without_the_theorem_is_not_accepted(self):
        # con-leche exits 0 on an export that declares nothing.
        export = conleche.export(self.lean, self.dir, TOOLS)
        export.write_text(export.read_text().splitlines()[0] + "\n")
        result = conleche.check_export(export, self.theorem, TOOLS)
        self.assertFalse(result["accepted"])
        self.assertIn("does not declare", result["detail"])

    def test_a_false_certificate_never_reaches_the_export(self):
        false_claim = self.lean.replace("1427119200000000", "1527119200000000")
        self.assertNotEqual(false_claim, self.lean, 'the negative control must change its premise')
        result = conleche.check(false_claim, TOOLS, self.dir)
        self.assertFalse(result["accepted"])
        self.assertIn("Lean did not accept", result["detail"])

    def test_checks_every_certificate_in_a_run(self):
        result = conleche.check_run(self.bundle, TOOLS, jobs=2, source=self.source)
        self.assertEqual(result["certificates"], len(self.bundle["findings"]))
        self.assertEqual(result["accepted"], result["certificates"], result["not_accepted"])
        self.assertEqual(result["checker"], "con-leche")
        self.assertEqual(result['checked'], result['total_findings'])
        self.assertTrue(result['passed'])

    def test_unrelated_true_theorem_cannot_replace_a_valid_finding_proof(self):
        changed = copy.deepcopy(self.certificate)
        changed['lean'] = ('namespace Cert.ConLecheFixture\n'
                           'theorem verified : True := by trivial\nend Cert.ConLecheFixture\n')
        result = conleche.check_run({'findings': [changed]}, TOOLS, source=self.source)
        self.assertFalse(result['passed'])
        self.assertEqual(result['accepted'], 0)
        self.assertEqual(result['checked'], 0)
        self.assertIn('differs from regeneration', result['not_accepted'][0]['detail'])

    def test_reversed_claim_and_unrelated_theorem_are_refused(self):
        changed = copy.deepcopy(self.certificate)
        changed['claim']['before'].reverse()
        changed['lean'] = 'namespace Cert.ConLecheFixture\ntheorem verified : True := by trivial\nend Cert.ConLecheFixture\n'
        result = conleche.check_run({'findings': [changed]}, TOOLS, source=self.source)
        self.assertFalse(result['passed'])
        self.assertIn('replay failed', result['not_accepted'][0]['detail'])

    def test_missing_proof_is_counted_and_fails_the_whole_run(self):
        missing = copy.deepcopy(self.certificate)
        missing['finding_id'] = 'MissingProof'
        missing.pop('lean')
        run = {'findings': [self.certificate, missing]}
        result = conleche.check_run(run, TOOLS, source=self.source)
        self.assertEqual((result['accepted'], result['checked'], result['total_findings']), (1, 1, 2))
        self.assertEqual(result['without_proof_text'], 1)
        self.assertEqual(len(result['not_accepted']), 1)
        self.assertFalse(result['passed'])
        path = self.dir / 'run.json'
        path.write_text(json.dumps(run))
        output = io.StringIO()
        with redirect_stdout(output), patch.object(conleche, 'Toolchain', return_value=TOOLS):
            code = conleche.main(['--run', str(path), '--facts', str(self.facts_path), '--jobs', '1'])
        self.assertEqual(code, 1)
        self.assertIn('1/2', output.getvalue())
        self.assertIn('1 not accepted', output.getvalue())

    def test_source_is_mandatory_and_duplicate_findings_fail(self):
        absent = conleche.check_run(self.bundle, TOOLS)
        self.assertFalse(absent['passed'])
        self.assertIn('facts source is required', absent['not_accepted'][0]['detail'])
        duplicate = conleche.check_run({'findings': [self.certificate, self.certificate]},
                                       TOOLS, source=self.source)
        self.assertEqual(duplicate['accepted'], 0)
        self.assertEqual(len(duplicate['not_accepted']), 2)
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            conleche.main(['--run', 'unused.json'])
        self.assertEqual(error.exception.code, 2)

    def test_snapshot_binding_and_missing_cited_row_fail_closed(self):
        wrong = conleche.check_run(dict(self.bundle, case={'facts_sha256':'a'*64}), TOOLS,
                                   source=self.source, facts_sha256='b'*64)
        self.assertFalse(wrong['passed'])
        self.assertIn('facts digest', wrong['not_accepted'][0]['detail'])
        changed = copy.deepcopy(self.certificate)
        changed['cited_facts'] = changed['cited_facts'][:-1]
        result = conleche.check_run({'findings':[changed]}, TOOLS, source=self.source)
        self.assertFalse(result['passed'])
        self.assertIn('cited facts', result['not_accepted'][0]['detail'])

    def test_empty_and_malformed_runs_never_pass(self):
        self.assertFalse(conleche.check_run({'findings':[]}, TOOLS, source=self.source)['passed'])
        malformed = conleche.check_run({'findings':[None, {'finding_id':'Invalid'}]},
                                       TOOLS, source=self.source)
        self.assertEqual(malformed['accepted'], 0)
        self.assertEqual(malformed['without_proof_text'], 2)
        with self.assertRaises(ValueError):
            conleche.check_run({}, TOOLS, source=self.source)

    def test_path_replacement_cannot_replay_other_bytes_under_original_digest(self):
        # A is the claimed input pathname. B has the opposite timestamp order
        # and its own valid certificate. Swap A->B->A around the real parser open.
        original = self.facts_path.read_bytes()
        data = json.loads(original)
        data['facts'][0]['t'], data['facts'][1]['t'] = data['facts'][1]['t'], data['facts'][0]['t']
        other = self.dir / 'other.json'
        other.write_text(json.dumps(data))
        other_source = JsonFacts(other)
        reversed_claim = copy.deepcopy(self.certificate['claim'])
        reversed_claim['before'].reverse()
        cert = check(reversed_claim, 'OtherSnapshot', other_source, out_dir=self.dir)
        self.assertEqual(cert['status'], 'verified')
        cert['lean'] = (self.dir / cert['lean_file']).read_text()
        input_path = self.dir / 'supplied.json'
        input_path.write_bytes(original)
        run_path = self.dir / 'swapped-run.json'
        run_path.write_text(json.dumps({'findings':[cert]}))
        real_open = conleche.open_source
        opened = []

        def swapping_open(path):
            opened.append(Path(path))
            input_path.write_bytes(other.read_bytes())
            try:
                return real_open(path)
            finally:
                input_path.write_bytes(original)

        with patch.object(conleche, 'open_source', side_effect=swapping_open), \
                patch.object(conleche, 'Toolchain', return_value=TOOLS), redirect_stdout(io.StringIO()):
            code = conleche.main(['--run', str(run_path), '--facts', str(input_path), '--jobs', '1'])
        self.assertEqual(code, 1)
        self.assertEqual(len(opened), 1)
        self.assertNotEqual(opened[0], input_path)
        self.assertEqual(input_path.read_bytes(), original)

    def test_theorem_name_needs_exactly_one_namespace(self):
        self.assertEqual(conleche.theorem_name(self.lean), self.theorem)
        with self.assertRaises(ValueError):
            conleche.theorem_name("theorem verified : True := trivial")


if __name__ == "__main__":
    unittest.main()
