"""Public final-field mappings preserve shape and exact source/set meanings."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from agent.answer_projection import catalog, claim_digest, project_answers, render_projection
from agent.answer_requirements import check, inspect
from checker.facts import Fact, FactSource

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = {'image': '4Dell Latitude CPi.E01', 'exhibit': 'HACK-PC',
          'source_snapshot': 'base-volume', 'source_variant': 'primary'}


def without_annotations(value):
    if isinstance(value, dict):
        return {key: without_annotations(child) for key, child in value.items() if not key.startswith('x-claim-')}
    if isinstance(value, list): return [without_annotations(child) for child in value]
    return value


class HackingFinalFields(unittest.TestCase):
    def setUp(self):
        self.public = json.loads((ROOT / 'eval/hacking_case_strict_draft/questions.json').read_text())
        self.questions = {q['id']: q for q in self.public['questions']}

    def leaf(self, qid):
        return next(iter(self.questions[qid]['answer_schema']['properties'].values()))

    def test_public_context_derivative_preserves_brief_and_matches_case(self):
        from agent.case import read_profile, with_questions
        original = json.loads((ROOT / 'eval/hacking_case/case-profile.json').read_text())
        path = ROOT / 'eval/hacking_case_strict_draft/case-profile.json'
        derivative = json.loads(path.read_text())
        self.assertEqual(dict(derivative, case_id=original['case_id']), original)
        self.assertEqual(derivative['case_id'], self.public['case_id'])
        context = with_questions(read_profile(path), self.public)
        self.assertEqual(context.case_id, self.public['case_id'])
        self.assertTrue(context.brief.startswith(original['brief']))

    def test_original_prompts_shapes_matching_rules_and_held_status_preserved(self):
        original = json.loads((ROOT / 'eval/hacking_case/questions.json').read_text())
        self.assertEqual(without_annotations(self.public['questions']), without_annotations(original['questions']))
        review = json.loads((ROOT / 'eval/hacking_case_strict_draft/review.json').read_text())
        self.assertIs(review['model_run_ready'], False)
        self.assertEqual(review['counts']['leaf_status'], {'catalog_support': 14, 'no_catalog_support': 24})
        statuses = []
        for question in self.public['questions']:
            view = inspect(question['answer_schema'], catalog()['forms'],
                           require_claim_requirements=True, require_evidence_scope=True)
            statuses.extend(row['status'] for row in view['requirements'])
        self.assertEqual(statuses.count('catalog_support'), 14)
        self.assertEqual(statuses.count('no_catalog_support'), 24)
        self.assertFalse(any(status in ('invalid', 'missing_annotation') for status in statuses))

    def test_new_roles_refuse_generic_timezone_or_cache_filename(self):
        for qid, role, old in [('Q4', 'os_effective_time_zone', 'os_time_zone_setting'),
                               ('Q27', 'browser_yahoo_mail_cache_file_name', 'browser_cache_file_name')]:
            requirement = self.leaf(qid)['x-claim-requirement']
            semantic = 'recorded_attribute_' + role + '_string'
            self.assertEqual(check(requirement, 'attributeRecorded', 'value', semantic)['status'], 'compatible')
            for index in range(8):
                self.assertEqual(check(requirement, 'attributeTuple', 'value_' + str(index), semantic)['status'], 'compatible')
            self.assertEqual(check(requirement, 'attributeRecorded', 'value', 'recorded_attribute_' + old + '_string')['status'], 'incompatible')

    def aggregate(self, definition=None, q28=True, q29=True, second_candidate=False):
        definition = definition if definition is not None else 'Exact bounded declared extraction population'
        strings = {10: 'fixture-declared-set', 20: definition, 30: 'member-A', 31: 'member-B'}
        class MemorySource(FactSource):
            def all(self): return list(self.rows.values())
            def get(self, ids): return {fid: self.rows[fid] for fid in ids if fid in self.rows}
            def string(self, sid): return strings[sid]
        source = MemorySource()
        source.rows = {row.id: row for row in [
            Fact(1, 'filesystemSet', 100000000, 1, 10, 20, ORIGIN),
            Fact(2, 'filesystemMemberDeleted', 100000000, 1, 10, 30, ORIGIN),
            Fact(3, 'filesystemMemberAllocated', 100000000, 1, 10, 31, ORIGIN)]}
        candidates = [{'candidate_id': 'C', 'claim': {'filesystemSetDeleted': [1, 2, False]}}]
        if second_candidate: candidates.append({'candidate_id': 'D', 'claim': {'filesystemSetDeleted': [1, 2, False]}})
        bindings = []
        for enabled, qid, field, path in [(q28, 'Q28', 'count', ['executable_file_count']),
                                          (q29, 'Q29', 'all_deleted', ['deleted_from_file_system'])]:
            if enabled:
                cid = 'D' if second_candidate and qid == 'Q28' else 'C'
                bindings.append({'candidate_id': cid, 'question_id': qid, 'path': path, 'field': field,
                                 'claim_sha256': claim_digest(candidates[0]['claim'])})
        public = dict(self.public, questions=[self.questions['Q28'], self.questions['Q29']])
        return project_answers(public, candidates, bindings, source, require_claim_requirements=True,
                               require_evidence_scope=True, evidence_facts_sha256='a' * 64)

    def test_valid_declared_aggregate_cannot_answer_unestablished_original_population(self):
        result = self.aggregate()
        self.assertEqual([row['status'] for row in result['submission']['answers']], ['unknown', 'unknown'])
        self.assertEqual(result['leaves'], [])
        fields = result['projection']['candidates']['C']['parts'][0]['fields']
        self.assertEqual(fields['count']['value'], 2)
        self.assertIs(fields['all_deleted']['value'], False)
        self.assertEqual(fields['count']['record_ids'], [1, 2, 3])
        self.assertEqual(fields['all_deleted']['record_ids'], [1, 2, 3])
        self.assertEqual({row['reason'] for row in result['unsupported']}, {'claim_role_does_not_meet_public_requirement'})

    def test_wrong_set_definition_and_legacy_count_cannot_supply_these_fields(self):
        result = self.aggregate(definition='Only a filename extension or a different population')
        self.assertEqual([row['status'] for row in result['submission']['answers']], ['unknown', 'unknown'])
        for qid in ('Q28', 'Q29'):
            requirement = self.leaf(qid)['x-claim-requirement']
            self.assertEqual(check(requirement, 'attributeRecorded', 'value',
                'recorded_attribute_recycle_executable_count_integer')['status'], 'incompatible')
            self.assertTrue(all(role.startswith('needs_') for role in requirement['semantic_types']))

    def test_omitted_or_foreign_q28_count_freezes_q29_before_filtering(self):
        for kwargs in ({'q28': False}, {'second_candidate': True}):
            result = self.aggregate(**kwargs)
            self.assertEqual(result['submission']['answers'][1]['status'], 'unknown')
            replayed = render_projection(result['projection'], admitted_ids=['C'])
            self.assertEqual(replayed['submission']['answers'][1]['status'], 'unknown')
            self.assertEqual(replayed['conflicts'], result['conflicts'])
