"""Q51 partial fields require a coherent, exact-origin Recycle Bin index tuple."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from agent.answer_projection import claim_digest, project_answers
from checker.catalog import ROLES
from checker.check import check
from checker.facts import JsonFacts
from tests.fixtures.contracts.scope_contract import apply_data_leakage_scopes
from extractor.attributes import emit_attribute
from extractor.store import Evidence
from verifier.verify import verify

ROOT = Path(__file__).resolve().parents[1]
ROLES_ORDER = ['recycle.index_file_name', 'recycle.original_path', 'recycle.index_deleted_at']
VALUES = ['$IABC123.bin', r'C:\Synthetic\document.bin', '2001-02-03T04:05:06Z']


class Q51PublicMembership(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        part = json.loads((ROOT / 'tests/fixtures/contracts/data-leakage/parts/q41_60.json').read_text())
        question = next(q for q in part['questions'] if q['id'] == 'Q51')
        plan = json.loads((ROOT / 'tests/fixtures/contracts/data-leakage/scope_plan.json').read_text())
        apply_data_leakage_scopes([question], plan)  # in-memory only; never assemble/write derivatives
        self.public = {'schema_version': 2, 'case_id': 'synthetic-q51', 'questions': [question]}
        self.identities = {}
        evidence = Evidence()
        for variant in ('primary', 'unallocated-recovery'):
            for role, value in zip(ROLES_ORDER, VALUES):
                self.identities[variant, role] = emit_attribute(
                    evidence, 'synthetic:PC:same-index-subject', role, value, 9_000_000_000,
                    artifact='synthetic Recycle Bin index', image='pc.E01', exhibit='PC',
                    source_snapshot='base-volume', source_variant=variant)
        evidence.write_json(self.root / 'facts.json', {})
        self.source = JsonFacts(self.root / 'facts.json')
        self.digest = hashlib.sha256((self.root / 'facts.json').read_bytes()).hexdigest()
        self.sequence = 0

    def entry(self, role, variant='primary'):
        identity = self.identities[variant, role]
        rows = {f.kind: f.id for f in self.source.all() if self.source.string(f.obj) == identity}
        spec = ROLES[role]
        return [rows['attributeSubject'], rows[spec.kind], rows[spec.value_kind], role]

    def tuple(self, roles=ROLES_ORDER, variant='primary'):
        return {'attributeTuple': [self.entry(role, variant) for role in roles]}

    def candidate(self, claim):
        self.sequence += 1
        return {'candidate_id': 'Index' + str(self.sequence), 'claim': claim}

    def certify(self, candidate):
        cert = check(candidate['claim'], candidate['candidate_id'], self.source, out_dir=self.root)
        self.assertEqual(cert['status'], 'verified', cert)
        self.assertEqual(cert['trust_tier'], 'kernel')
        self.assertEqual(cert['axioms'], [])
        self.assertEqual(verify(cert, self.source), [])

    def project(self, candidate, fields=None, certify=True):
        if certify:
            self.certify(candidate)
        fields = fields or [('original_path', 'value_1')]
        bindings = [dict(candidate_id=candidate['candidate_id'], claim_sha256=claim_digest(candidate['claim']),
                         question_id='Q51', path=['records', 0, field], part=0, field=selector)
                    for field, selector in fields]
        return project_answers(self.public, [candidate], bindings, self.source,
                               require_claim_requirements=True, require_evidence_scope=True,
                               evidence_facts_sha256=self.digest)

    def test_primary_and_unallocated_recovery_each_support_full_index_row(self):
        for variant in ('primary', 'unallocated-recovery'):
            with self.subTest(variant=variant):
                result = self.project(self.candidate(self.tuple(variant=variant)),
                                      [('i_filename', 'value_0'), ('original_path', 'value_1'),
                                       ('deleted_at', 'value_2')])
                self.assertFalse(result['unsupported'])
                self.assertEqual(result['submission']['answers'][0]['answer'], {'records': [
                    dict(i_filename=VALUES[0], original_path=VALUES[1], deleted_at=VALUES[2])]})
                for leaf in result['leaves']:
                    origins = leaf['scope_checks'][0]['record_origins']
                    self.assertTrue(all(origin['source_variant'] == variant for origin in origins))

    def test_partial_path_still_requires_full_tuple_and_does_not_invent_siblings(self):
        result = self.project(self.candidate(self.tuple()))
        self.assertFalse(result['unsupported'])
        self.assertEqual(result['submission']['answers'][0]['answer'],
                         {'records': [{'original_path': VALUES[1]}]})

    def test_verified_standalone_original_path_does_not_establish_index_membership(self):
        candidate = self.candidate({'attributeRecorded': self.entry('recycle.original_path')})
        result = self.project(candidate, [('original_path', 'value')])
        self.assertEqual(result['leaves'], [])
        self.assertEqual(result['submission']['answers'][0]['status'], 'unknown')

    def test_missing_or_other_atomic_part_cannot_supply_required_index_role(self):
        incomplete = self.tuple(ROLES_ORDER[:2])
        claims = [incomplete, {'both': [incomplete,
                  {'attributeRecorded': self.entry('recycle.index_deleted_at')}]}]
        for claim in claims:
            with self.subTest(claim=claim):
                result = self.project(self.candidate(claim))
                self.assertEqual(result['leaves'], [])
                self.assertEqual(result['unsupported'][0]['reason'], 'claim_attributes_do_not_meet_public_requirement')

    def test_same_subject_cannot_mix_primary_and_recovery_origins(self):
        entries = [self.entry(role) for role in ROLES_ORDER]
        entries[-1] = self.entry('recycle.index_deleted_at', 'unallocated-recovery')
        result = self.project(self.candidate({'attributeTuple': entries}))
        self.assertEqual(result['leaves'], [])
        self.assertEqual(result['submission']['answers'][0]['status'], 'unknown')
        self.assertEqual(result['unsupported'][0]['reason'], 'claim_supporting_records_have_mixed_origins')

    def test_duplicate_required_role_does_not_authorize_unchecked_partial_field(self):
        entries = [self.entry(role) for role in ROLES_ORDER] + [self.entry('recycle.original_path')]
        candidate = self.candidate({'attributeTuple': entries})
        cert = check(candidate['claim'], candidate['candidate_id'], self.source, out_dir=self.root)
        self.assertNotEqual(cert['status'], 'verified')
        result = self.project(candidate, certify=False)
        self.assertEqual(result['leaves'], [])
        self.assertEqual(result['unsupported'][0]['reason'], 'claim_attributes_do_not_meet_public_requirement')


if __name__ == '__main__':
    unittest.main()
