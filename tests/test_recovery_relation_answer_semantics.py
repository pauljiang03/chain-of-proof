"""Shared labels and serials never promote cross-source records to identity."""
import hashlib
from pathlib import Path
import tempfile
import unittest

from agent.answer_projection import claim_digest, claim_fields, project_answers, render_projection
from checker.check import check
from checker.facts import JsonFacts
from extractor.store import Evidence
from verifier.verify import verify


class RecoveryRelationAnswerSemantics(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.origins = [dict(image='A.E01', exhibit='A', source_snapshot='base-volume', source_variant='primary'),
                        dict(image='B.E01', exhibit='B', source_snapshot='base-volume', source_variant='primary')]
        evidence = Evidence()
        evidence.add('fileCreated', 100, 1, r'\file.txt', 'COLLIDING-SERIAL',
                     artifact='creation', partition_offset=0, **self.origins[0])
        evidence.add('fileCreated', 100, 1, r'\entry.txt', 'COLLIDING-AREA-LABEL',
                     artifact='entry', partition_offset=0, **self.origins[0])
        for index, origin in enumerate(self.origins):
            evidence.add('volumeRecorded', 10, 1, 'Separate disc observation', 'COLLIDING-SERIAL',
                         artifact='volume'+str(index), partition_offset=4096, **origin)
            evidence.add('unallocatedOnDevice', 10, 1, 'Separate examined device', 'COLLIDING-AREA-LABEL',
                         artifact='area'+str(index), partition_offset=4096, **origin)
        path = self.root / 'facts.json'
        evidence.write_json(path, {})
        self.source = JsonFacts(path)
        self.digest = hashlib.sha256(path.read_bytes()).hexdigest()
        self.ids = {row.prov['artifact']: row.id for row in self.source.all()}

    def project(self, candidate, selector, meaning, same_origin):
        form = next(iter(candidate['claim']))
        scope = {'mode': 'source_records', 'origins': self.origins}
        if same_origin:
            scope['same_origin'] = True
        public = {'schema_version': 2, 'case_id': 'synthetic-recorded-relations', 'questions': [{
            'id': 'Q1', 'prompt': 'Does the stated relation between the source observations hold?',
            'answer_schema': {'type': 'boolean', 'x-claim-scope': scope,
                'x-claim-requirement': {'semantic_types': [meaning],
                    'selectors': [{'form': form, 'field': selector}],
                    'meaning': 'A literal recorded-value relation only.',
                    'evidence_needed': 'The two source records with their declared meanings.'}}}]}
        binding = {'candidate_id': candidate['candidate_id'], 'claim_sha256': claim_digest(candidate['claim']),
                   'question_id': 'Q1', 'path': [], 'field': selector}
        return project_answers(public, [candidate], [binding], self.source,
                               require_claim_requirements=True, require_evidence_scope=True,
                               evidence_facts_sha256=self.digest)

    def exercise(self, form, first, second, field, old_field, old_scalars, stronger):
        for index in range(2):
            with self.subTest(form=form, cross_image=bool(index)):
                row = {'candidate_id': form+str(index), 'claim': {form: [
                    self.ids[first], self.ids[second+str(index)]]}}
                certificate = check(row['claim'], row['candidate_id'], self.source, out_dir=self.root)
                self.assertEqual(certificate['status'], 'verified')
                self.assertEqual(certificate['trust_tier'], 'kernel')
                problems = verify(certificate, self.source)
                self.assertEqual(problems, [])
                # index 0 reproduces identical public origin axes with a different
                # partition. The guard is not an object/partition identity proof.
                a = self.project(row, field, field, same_origin=index == 0)
                self.assertFalse(a['unsupported'])
                self.assertIs(a['submission']['answers'][0]['answer'], True)
                b = render_projection(a['projection'], admitted_ids=[row['candidate_id']],
                                      authority='recorded_certificates')
                self.assertEqual(a['submission'], b['submission'])
                for selector, meaning in [(old_field, old_field), (old_field, field),
                                           (field, old_field), (field, stronger)]:
                    rejected = self.project(row, selector, meaning, same_origin=index == 0)
                    self.assertEqual(rejected['submission']['answers'][0]['status'], 'unknown')
                    self.assertEqual(rejected['leaves'], [])
                fields = claim_fields(row['claim'], self.source)['parts'][0]['fields']
                for alias in old_scalars:
                    self.assertNotIn(alias, fields)
                self.assertEqual(fields['creation_recorded_time_us']['value'], 100)

    def test_time_order_and_equal_serial_do_not_identify_a_volume_or_disc(self):
        self.exercise('createdAfterVolumeRecord', 'creation', 'volume',
                      'recorded_time_order_with_matching_volume_serials',
                      'creation_timestamp_after_volume_record', ('disc', 'volume', 'creation_time_us'),
                      'creation_on_the_same_physical_disc_after_volume_record')

    def test_equal_recovery_area_labels_do_not_identify_recovery_device(self):
        self.exercise('recoveredOnDevice', 'entry', 'area',
                      'matching_recorded_recovery_area_labels', 'entry_recovered_from_device',
                      ('device_serial', 'creation_time_us'), 'same_physical_recovery_device')


if __name__ == '__main__':
    unittest.main()
