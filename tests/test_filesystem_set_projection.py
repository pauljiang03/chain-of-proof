"""Set projection preserves assertions and binds every declared support record."""
from copy import deepcopy
from dataclasses import replace
import unittest
from unittest.mock import patch

from agent.answer_projection import claim_fields, prepare_projection, render_projection
from tests.test_answer_projection import candidate, bind
from tests.test_filesystem_set import Source, row

ORIGIN = {'image': 'image-A', 'exhibit': 'PC', 'source_snapshot': 'base-volume', 'source_variant': 'primary'}
RECOVERED = dict(ORIGIN, source_variant='unallocated-recovery')
DEFINITION = 'completed namespace traversal; distinct .exe members with MZ headers'


def public():
    questions = []
    for qid, field, kind, semantic in (
            ('Q28', 'count', 'integer', 'asserted_declared_filesystem_set_count'),
            ('Q29', 'all_deleted', 'boolean', 'asserted_all_members_deleted_in_declared_filesystem_set')):
        leaf = {'type': kind, 'x-claim-requirement': {
            'semantic_types': [semantic], 'selectors': [{'form': 'filesystemSetDeleted', 'field': field}],
            'meaning': 'Exact declared file set observation.', 'evidence_needed': 'One declared set and its complete membership.',
            'field_conditions': [{'field': 'definition', 'semantic_type': 'declared_filesystem_set_extraction_definition',
                                  'values': [DEFINITION]}]}}
        if qid == 'Q29':
            leaf['x-claim-reference'] = {'mode': 'same_claim_part', 'question_id': 'Q28', 'path': ['count']}
        questions.append({'id': qid, 'prompt': 'Declared set?', 'answer_schema': {
            'type': 'object', 'properties': {field: leaf}, 'x-claim-row': {'mode': 'same_claim_part'},
            'x-claim-scope': {'mode': 'source_records', 'origins': [ORIGIN]}}})
    return {'schema_version': 2, 'case_id': 'synthetic-set', 'questions': questions}


class FilesystemSetProjection(unittest.TestCase):
    def setUp(self):
        self.source = Source([replace(row(1, 'filesystemSet'), prov=deepcopy(ORIGIN)),
                              replace(row(2, 'filesystemMemberDeleted', aux=101), prov=deepcopy(ORIGIN)),
                              replace(row(3, 'filesystemMemberAllocated', aux=102), prov=deepcopy(ORIGIN)),
                              replace(row(4, 'filesystemMemberDeleted', obj=20), prov=deepcopy(RECOVERED))])

    def plan(self, claim=None, contract=None, bindings=None):
        c = candidate('SET', claim or {'filesystemSetDeleted': [1, 2, False]})
        bindings = bindings if bindings is not None else [
            bind(c, 'Q28', ['count'], 'count'), bind(c, 'Q29', ['all_deleted'], 'all_deleted')]
        return prepare_projection(contract or public(), [c], bindings, self.source,
                                  require_claim_requirements=True, require_evidence_scope=True,
                                  evidence_facts_sha256='a' * 64)

    def test_wrong_count_and_boolean_preserved_without_truth_feedback(self):
        with patch('checker.claims.parse', side_effect=AssertionError('no checking')), \
             patch('checker.claims.census_satisfied', side_effect=AssertionError('no truth feedback')):
            plan = self.plan({'filesystemSetDeleted': [1, 999, True]})
        result = render_projection(plan)
        self.assertEqual([r['answer'] for r in result['submission']['answers']], [{'count': 999}, {'all_deleted': True}])
        for leaf in result['leaves']:
            self.assertEqual(leaf['record_ids'], [1, 2, 3])
        self.assertEqual([r['id'] for r in plan['candidates']['SET']['records']], [1, 2, 3])
        self.assertEqual(render_projection(plan, admitted_ids=[], authority='independently_replayed')['leaves'], [])

    def test_boolean_shape_is_exact_and_missing_declaration_stays_missing(self):
        for value in (0, 1, 'false', None):
            projected = claim_fields({'filesystemSetDeleted': [1, 2, value]}, self.source)
            self.assertEqual(projected['unsupported'][0]['reason'], 'unsupported_or_malformed_claim')
        projected = claim_fields({'filesystemSetDeleted': [999, 2, False]}, self.source)
        self.assertEqual(projected['missing_record_ids'], [999])
        fields = projected['parts'][0]['fields']
        self.assertIs(fields['all_deleted']['value'], False)
        self.assertEqual(fields['all_deleted']['record_ids'], [999])
        self.assertNotIn('definition', fields)

    def test_every_member_origin_is_checked_even_for_literal_count(self):
        self.source.rows[2] = replace(self.source.rows[2], prov=deepcopy(RECOVERED))
        result = render_projection(self.plan())
        self.assertEqual(result['leaves'], [])
        self.assertEqual({r['reason'] for r in result['unsupported']}, {'claim_records_do_not_meet_public_scope'})

    def test_same_origin_accepts_each_alternative_but_refuses_mixed_support(self):
        contract = public()
        for q in contract['questions']:
            q['answer_schema']['x-claim-scope'].update(origins=[ORIGIN, RECOVERED], same_origin=True)
        self.assertEqual(len(render_projection(self.plan(contract=contract))['leaves']), 2)
        self.source.rows[2] = replace(self.source.rows[2], prov=deepcopy(RECOVERED))
        result = render_projection(self.plan(contract=contract))
        self.assertEqual({r['reason'] for r in result['unsupported']}, {'claim_supporting_records_have_mixed_origins'})
        self.source.rows[:3] = [replace(r, prov=deepcopy(RECOVERED)) for r in self.source.rows[:3]]
        self.assertEqual(len(render_projection(self.plan(contract=contract))['leaves']), 2)

    def test_wrong_set_definition_cannot_supply_either_related_field(self):
        self.source.rows[0] = replace(self.source.rows[0], aux=101)
        result = render_projection(self.plan())
        self.assertEqual(result['leaves'], [])
        self.assertEqual({r['reason'] for r in result['unsupported']}, {'claim_fields_do_not_meet_public_requirement'})

    def test_missing_count_binding_cannot_leave_dependent_boolean(self):
        c = candidate('SET', {'filesystemSetDeleted': [1, 2, False]})
        result = render_projection(self.plan(bindings=[bind(c, 'Q29', ['all_deleted'], 'all_deleted')]))
        self.assertEqual(result['leaves'], [])
        self.assertEqual(result['conflicts'][0]['reference_status'], 'absent')


if __name__ == '__main__':
    unittest.main()
