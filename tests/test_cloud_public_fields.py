"""Approved cloud source observations respect the unchanged public meanings."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from agent.answer_projection import claim_digest, project_answers, render_projection
from checker.catalog import ROLES
from checker.check import check
from checker.facts import JsonFacts
from extractor.attributes import emit_attribute
from extractor.store import Evidence
from verifier.verify import verify

CONTAINER = ['cloud.container.service', 'cloud.container.type', 'cloud.container.path']
DELETION = ['cloud.google_drive.document_id', 'cloud.google_drive.file_name',
            'cloud.google_drive.deletion_record_server_modified_at']
CREDENTIALS = ['cloud.google_drive.credentials_account', 'cloud.google_drive.credentials_used_at']


class CloudPublicFields(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        public = json.loads((Path(__file__).resolve().parent / 'fixtures/contracts/data-leakage/questions.json').read_text())
        cls.public = dict(public, questions=[q for q in public['questions'] if q['id'] in ('Q29', 'Q30', 'Q31')])
        q29 = next(q for q in cls.public['questions'] if q['id'] == 'Q29')
        cls.origin = q29['answer_schema']['x-claim-scope']['origins'][0]

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        evidence = Evidence()
        self.identities = {}
        groups = [('container', CONTAINER, ['Google Drive', 'validated client log', '/synthetic/sync.log']),
                  ('deletion', DELETION, ['synthetic-doc-42', 'fixture.txt', '2001-02-03T04:05:06Z']),
                  ('credentials', CREDENTIALS, ['fixture@example.invalid', '2001-02-03T04:05:06Z'])]
        for group, roles, values in groups:
            for role, value in zip(roles, values):
                self.identities[group, role] = emit_attribute(evidence, 'synthetic:'+group, role, value, 100,
                    artifact='synthetic retained cloud fixture', **self.origin)
        self.identities['other', CONTAINER[0]] = emit_attribute(evidence, 'synthetic:other-container', CONTAINER[0],
            'Google Drive', 100, artifact='synthetic other container', **self.origin)
        foreign = dict(self.origin, exhibit='FOREIGN', image='foreign.E01')
        for role, value in zip(CONTAINER, ['Google Drive', 'validated client log', '/synthetic/foreign.log']):
            self.identities['foreign', role] = emit_attribute(evidence, 'synthetic:foreign-container', role,
                value, 100, artifact='synthetic foreign container', **foreign)
        evidence.write_json(self.root/'facts.json', {})
        self.source = JsonFacts(self.root/'facts.json')
        self.digest = hashlib.sha256((self.root/'facts.json').read_bytes()).hexdigest()
        self.sequence = 0

    def entry(self, group, role):
        identity = self.identities[group, role]
        rows = {fact.kind: fact.id for fact in self.source.all() if self.source.string(fact.obj) == identity}
        spec = ROLES[role]
        return [rows['attributeSubject'], rows[spec.kind], rows[spec.value_kind], role]

    def tuple(self, group, roles):
        return {'attributeTuple': [self.entry(group, role) for role in roles]}

    def candidate(self, claim):
        self.sequence += 1
        return {'candidate_id': 'C'+str(self.sequence), 'claim': claim}

    def certify(self, row, accepted=True):
        cert = check(row['claim'], row['candidate_id'], self.source, out_dir=self.root)
        self.assertEqual(cert['status'] == 'verified', accepted, cert)
        if accepted:
            self.assertEqual(cert['trust_tier'], 'kernel')
            self.assertEqual(cert['axioms'], [])
            self.assertEqual(verify(cert, self.source), [])
        return cert

    def project(self, row, qid, fields):
        bindings = [{'candidate_id': row['candidate_id'], 'claim_sha256': claim_digest(row['claim']),
            'question_id': qid, 'path': path, 'field': field, 'part': 0} for path, field in fields]
        return project_answers(self.public, [row], bindings, self.source, require_claim_requirements=True,
                               require_evidence_scope=True, evidence_facts_sha256=self.digest)

    def answer(self, result, qid):
        return next(row for row in result['submission']['answers'] if row['question_id'] == qid)

    def test_valid_container_tuple_supplies_coherent_partial_fields(self):
        row = self.candidate(self.tuple('container', CONTAINER))
        self.certify(row)
        for field, index in [('service', 0), ('type', 1), ('path', 2)]:
            result = self.project(row, 'Q29', [(['traces', 0, field], 'value_'+str(index))])
            self.assertFalse(result['unsupported'])
            self.assertEqual(len(result['leaves']), 1)
        result = self.project(row, 'Q29', [(['traces', 0, field], 'value_'+str(index))
                                          for index, field in enumerate(('service', 'type', 'path'))])
        answer = self.answer(result, 'Q29')['answer']['traces'][0]
        self.assertEqual(answer, {'service': 'Google Drive', 'type': 'validated client log', 'path': '/synthetic/sync.log'})
        self.assertNotIn('deleted', answer)

    def test_standalone_path_and_tuple_missing_service_cannot_qualify(self):
        claims = [({'attributeRecorded': self.entry('container', CONTAINER[2])}, 'value'),
                  (self.tuple('container', CONTAINER[1:]), 'value_1')]
        for claim, field in claims:
            row = self.candidate(claim); self.certify(row)
            result = self.project(row, 'Q29', [(['traces', 0, 'path'], field)])
            self.assertEqual(self.answer(result, 'Q29')['status'], 'unknown')
            self.assertTrue(result['unsupported'])

    def test_mixed_subject_tuple_is_literal_a_but_checker_and_b_refuse(self):
        claim = self.tuple('container', CONTAINER)
        claim['attributeTuple'][0] = self.entry('other', CONTAINER[0])
        row = self.candidate(claim); self.certify(row, accepted=False)
        a = self.project(row, 'Q29', [(['traces', 0, 'path'], 'value_2')])
        self.assertEqual(self.answer(a, 'Q29')['answer'], {'traces': [{'path': '/synthetic/sync.log'}]})
        b = render_projection(a['projection'], admitted_ids=[], authority='recorded_certificates')
        self.assertEqual(self.answer(b, 'Q29')['status'], 'unknown')

    def test_foreign_origin_tuple_remains_certified_but_not_selected_public_source(self):
        row = self.candidate(self.tuple('foreign', CONTAINER)); self.certify(row)
        result = self.project(row, 'Q29', [(['traces', 0, 'path'], 'value_2')])
        self.assertEqual(self.answer(result, 'Q29')['status'], 'unknown')
        self.assertEqual(result['unsupported'][0]['reason'], 'claim_records_do_not_meet_public_scope')

    def test_credentials_account_is_partial_but_credential_use_time_is_not_logon(self):
        row = self.candidate({'attributeRecorded': self.entry('credentials', CREDENTIALS[0])})
        self.certify(row)
        result = self.project(row, 'Q31', [(['account'], 'value')])
        self.assertEqual(self.answer(result, 'Q31')['answer'], {'account': 'fixture@example.invalid'})
        used = self.candidate({'attributeRecorded': self.entry('credentials', CREDENTIALS[1])})
        self.certify(used)
        result = self.project(used, 'Q31', [(['logon_time'], 'value')])
        self.assertEqual(self.answer(result, 'Q31')['status'], 'unknown')
        self.assertTrue(result['unsupported'])

    def test_joined_deletion_related_literals_do_not_establish_original_q30_meanings(self):
        row = self.candidate(self.tuple('deletion', DELETION)); self.certify(row)
        result = self.project(row, 'Q30', [(['files', 0, 'filename'], 'value_1'),
            (['files', 0, 'deleted_at'], 'value_2'), (['files', 0, 'modified_at'], 'value_2')])
        self.assertEqual(self.answer(result, 'Q30')['status'], 'unknown')
        self.assertEqual(len(result['unsupported']), 3)
        self.assertEqual(result['leaves'], [])


if __name__ == '__main__':
    unittest.main()
