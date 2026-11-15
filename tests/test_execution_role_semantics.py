"""Execution-artifact fields need fixed roles, not persuasive provenance text."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from checker import check as checker
from checker.catalog import ROLES
from checker.facts import JsonFacts, KINDS
from extractor.attributes import emit_attribute
from extractor.store import Evidence
from verifier.verify import verify


class ExecutionRoleSemantics(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        ev = Evidence()
        self.identities = {}
        provenance = dict(artifact='Security.evtx record 42', source='Security event log: process creation',
                          time_meaning='time the process was created', source_event_time_us=20_000_000)
        for key, subject, role, value in (
            ('name', 'image-A:Security.evtx:42', 'app.execution.program', 'fixture.exe'),
            ('path', 'image-A:Security.evtx:42', 'app.execution.path', r'C:\tools\fixture.exe'),
            ('other', 'image-A:Security.evtx:43', 'app.execution.path', r'C:\other\fixture.exe'),
            ('ordinary', 'image-A:MuiCache', 'app.name', 'fixture.exe'),
        ):
            self.identities[key] = (emit_attribute(ev, subject, role, value, 100_000_000,
                                                  **provenance), role)
        # Execution-looking provenance does not change this legacy mixed-source kind.
        ev.add('programRun', 20_000_000, 1, 'fixture.exe', r'C:\tools\fixture.exe',
               executed_flag=True, **provenance)
        ev.write_json(self.root / 'facts.json', {})
        self.source = JsonFacts(self.root / 'facts.json')
        self.legacy = next(f.id for f in self.source.all() if f.kind == 'programRun')
        self.sequence = 0

    def triple(self, name):
        identity, role = self.identities[name]
        rows = {f.kind: f.id for f in self.source.all() if self.source.string(f.obj) == identity}
        return [rows['attributeSubject'], rows[ROLES[role].kind], rows['attributeTextValue']]

    def claim(self, name):
        return {'attributeRecorded': self.triple(name) + [self.identities[name][1]]}

    def certify(self, claim, accepted=True):
        self.sequence += 1
        with patch('checker.check.run_kernel', wraps=checker.run_kernel) as kernel:
            result = checker.check(claim, f'ExecutionRole{self.sequence}', self.source, out_dir=self.root)
        self.assertTrue(kernel.called, 'semantic acceptance/refusal must reach the real kernel')
        self.assertEqual(result['status'], 'verified' if accepted else 'rejected', result)
        if accepted:
            self.assertEqual(result['trust_tier'], 'kernel')
            self.assertEqual(result['axioms'], [])
            self.assertEqual(verify(result, self.source), [])
        return result

    def test_typed_execution_artifact_fields_verify_with_narrow_scope(self):
        start = KINDS.index('roleAppBinaryFileVersion') + 1
        self.assertEqual(KINDS[start:start + 2], ('roleAppExecutionProgram', 'roleAppExecutionPath'))
        for name in ('name', 'path'):
            cert = self.certify(self.claim(name))
            self.assertIn('execution artifact', cert['english'])
            self.assertIn('actual code execution', cert['english'])
            self.assertIn('physical user', cert['english'])
            self.assertIn('examined', cert['english'])
            self.assertEqual({row['t'] for row in cert['cited_facts']}, {100_000_000})
            self.assertEqual({row['prov']['source_event_time_us'] for row in cert['cited_facts']},
                             {20_000_000})
        joined = {'attributesSameSubject': self.triple('name') + ['app.execution.program']
                  + self.triple('path') + ['app.execution.path']}
        self.certify(joined)

    def test_true_execution_provenance_without_a_new_role_is_still_only_observation(self):
        legacy = self.certify({'programRan': [self.legacy]})
        self.assertIn('application observation', legacy['english'])
        self.assertIn('does not establish execution at that time', legacy['english'])
        self.assertNotIn('recorded execution time for', legacy['english'])
        subject, _, value = self.triple('path')
        self.certify({'attributeRecorded': [subject, self.legacy, value, 'app.execution.path']},
                     accepted=False)

    def test_ordinary_name_or_other_execution_role_cannot_be_relabelled(self):
        self.certify({'attributeRecorded': self.triple('ordinary') + ['app.execution.program']},
                     accepted=False)
        self.certify({'attributeRecorded': self.triple('name') + ['app.execution.path']},
                     accepted=False)

    def test_execution_fields_from_different_source_records_cannot_be_joined(self):
        joined = {'attributesSameSubject': self.triple('name') + ['app.execution.program']
                  + self.triple('other') + ['app.execution.path']}
        self.certify(joined, accepted=False)


if __name__ == '__main__':
    unittest.main()
