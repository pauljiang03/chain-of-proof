"""Serial collisions support recorded equality, never volume/device identity."""
import hashlib
from pathlib import Path
import tempfile
import unittest

from agent.answer_projection import catalog, claim_digest, claim_fields
from agent.tools import FORMS
from checker.check import check
from checker.facts import JsonFacts
from comparison.ablation.projection import project_a, project_b
from extractor.store import Evidence
from verifier.verify import verify


EQUALITY = 'matching_recorded_volume_serials'


class VolumeSerialAnswerSemantics(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.origins = [dict(image='PC.E01', exhibit='PC', source_snapshot='base-volume', source_variant='primary'),
                        dict(image='CLONE.E01', exhibit='CLONE', source_snapshot='base-volume', source_variant='primary')]
        evidence = Evidence()
        evidence.add('volumeSeen', 10, 1, 'Original volume label', 'DEADBEEF',
                     artifact='synthetic PC volume record', **self.origins[0])
        evidence.add('volumeOnDevice', 20, 1, 'Distinct examined device', 'DEADBEEF',
                     artifact='synthetic cloned volume record', **self.origins[1])
        evidence.add('volumeOnDevice', 30, 1, 'Other examined device', '12345678',
                     artifact='synthetic different serial record', **self.origins[1])
        evidence.add('lnkTarget', 40, 1, r'C:\report.txt', 'DEADBEEF',
                     artifact='synthetic shortcut from original volume', **self.origins[0])
        for serial, suffix in [('DEADBEEF', 'collision'), ('12345678', 'different')]:
            evidence.add('volumeMount', 50, 1, 'Mapping '+suffix, serial,
                         artifact='synthetic mapping from other volume', **self.origins[1])
        evidence.add('volumeSeen', 60, 1, 'Different volume label', '12345678',
                     artifact='synthetic different serial PC record', **self.origins[0])
        path = self.root / 'facts.json'
        evidence.write_json(path, {})
        self.source = JsonFacts(path)
        self.digest = hashlib.sha256(path.read_bytes()).hexdigest()
        self.ids = {self.source.string(row.obj): row.id for row in self.source.all()}

    def candidate(self, other='Distinct examined device'):
        return {'candidate_id': 'Comparison', 'claim': {'recordedOnDevice': [
            self.ids['Original volume label'], self.ids[other]]}}

    def public(self, semantic_type=EQUALITY, selector=EQUALITY, form='recordedOnDevice'):
        return {'schema_version': 2, 'case_id': 'synthetic-serial-collision', 'questions': [{
            'id': 'Q1', 'prompt': 'Do these source records carry equal volume serial values?',
            'answer_schema': {'type': 'boolean', 'x-claim-requirement': {
                'semantic_types': [semantic_type],
                'selectors': [{'form': form, 'field': selector}],
                'meaning': 'Equality of recorded serial values only.',
                'evidence_needed': 'The two cited volume records.'},
                'x-claim-scope': {'mode': 'source_records', 'origins': self.origins}}}]}

    def project(self, row, *, selector=EQUALITY, semantic_type=EQUALITY):
        binding = {'candidate_id': row['candidate_id'], 'claim_sha256': claim_digest(row['claim']),
                   'question_id': 'Q1', 'path': [], 'field': selector}
        form = next(iter(row['claim']))
        return project_a(self.public(semantic_type, selector, form), [row], [binding], self.source,
                         require_claim_requirements=True, require_evidence_scope=True,
                         evidence_facts_sha256=self.digest)

    def test_real_certificate_and_replay_preserve_only_collision_safe_equality(self):
        row = self.candidate()
        certificate = check(row['claim'], row['candidate_id'], self.source, out_dir=self.root)
        self.assertEqual(certificate['status'], 'verified')
        self.assertEqual(certificate['trust_tier'], 'kernel')
        self.assertEqual(certificate['axioms'], [])
        problems = verify(certificate, self.source)
        self.assertEqual(problems, [])
        projected = self.project(row)
        self.assertFalse(projected['unsupported'])
        self.assertIs(projected['submission']['answers'][0]['answer'], True)
        filtered = project_b(projected, [dict(row, status='verified', checker_status='verified',
                                             verification={'passed': not problems})])
        self.assertEqual(filtered['submission'], projected['submission'])
        fields = claim_fields(row['claim'], self.source)['parts'][0]['fields']
        self.assertEqual(fields['recorded_volume_serial']['value'], 'DEADBEEF')
        self.assertEqual(fields['recorded_volume_label']['value'], 'Original volume label')
        self.assertEqual(fields['examined_device_identifier']['value'], 'Distinct examined device')
        self.assertEqual(fields['examined_device_identifier']['semantic_type'],
                         'recorded_examined_device_identifier')
        self.assertNotIn('same_device_volume', fields)

    def test_old_identity_selector_and_old_semantic_type_both_refuse(self):
        row = self.candidate()
        for selector in ('same_device_volume', EQUALITY):
            result = self.project(row, selector=selector, semantic_type='same_device_volume')
            self.assertEqual(result['submission']['answers'][0]['status'], 'unknown')
            self.assertEqual(result['leaves'], [])
            self.assertTrue(result['unsupported'])
        fields = catalog()['forms']['recordedOnDevice']
        self.assertNotIn('same_device_volume', fields)
        self.assertNotIn('same_device_volume', {field['semantic_type'] for field in fields.values()})
        self.assertIn('does not identify the same volume', FORMS['recordedOnDevice'][1])

    def test_unchecked_wrong_equality_is_not_repaired_and_b_refuses_it(self):
        row = self.candidate('Other examined device')
        certificate = check(row['claim'], row['candidate_id'], self.source, out_dir=self.root)
        self.assertEqual(certificate['status'], 'rejected')
        a = self.project(row)
        self.assertIs(a['submission']['answers'][0]['answer'], True)
        b = project_b(a, [dict(row, status='rejected', checker_status='rejected', verification=None)])
        self.assertEqual(b['submission']['answers'][0]['status'], 'unknown')

    def test_shortcut_serial_collisions_never_restore_old_volume_associations(self):
        cases = [
            ('openedFromMount', 'Mapping collision', 'Mapping different',
             'opened_from_mounted_volume', 'shortcut_target_associated_with_mounted_volume'),
            ('openedFromDevice', 'Distinct examined device', 'Other examined device',
             'opened_from_device_volume', 'shortcut_target_associated_with_device_volume'),
            ('openedFromRecorded', 'Original volume label', 'Different volume label',
             'same_recorded_volume', 'shortcut_target_associated_with_recorded_volume')]
        for form, equal_name, different_name, old_field, old_type in cases:
            with self.subTest(form=form):
                row = {'candidate_id': form, 'claim': {form: [self.ids[r'C:\report.txt'], self.ids[equal_name]]}}
                certificate = check(row['claim'], form, self.source, out_dir=self.root)
                self.assertEqual(certificate['status'], 'verified')
                self.assertEqual(certificate['trust_tier'], 'kernel')
                problems = verify(certificate, self.source)
                self.assertEqual(problems, [])
                a = self.project(row)
                self.assertIs(a['submission']['answers'][0]['answer'], True)
                b = project_b(a, [dict(row, status='verified', checker_status='verified',
                                      verification={'passed': not problems})])
                self.assertEqual(a['submission'], b['submission'])
                for selector, meaning in [(old_field, old_type), (EQUALITY, old_type),
                                           (EQUALITY, old_field), (old_field, EQUALITY)]:
                    refused = self.project(row, selector=selector, semantic_type=meaning)
                    self.assertEqual(refused['submission']['answers'][0]['status'], 'unknown')
                wrong = {'candidate_id': form+'Wrong',
                         'claim': {form: [self.ids[r'C:\report.txt'], self.ids[different_name]]}}
                certificate = check(wrong['claim'], wrong['candidate_id'], self.source, out_dir=self.root)
                self.assertEqual(certificate['status'], 'rejected')
                a = self.project(wrong)
                self.assertIs(a['submission']['answers'][0]['answer'], True)
                b = project_b(a, [dict(wrong, status='rejected', checker_status='rejected', verification=None)])
                self.assertEqual(b['submission']['answers'][0]['status'], 'unknown')


if __name__ == '__main__':
    unittest.main()
