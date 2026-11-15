"""Public row policies bind identifiers and values to one atomic claim part."""
import tempfile
import unittest

from agent.answer_projection import catalog, claim_digest, project_answers
from agent.answer_requirements import inspect
from checker.facts import Fact, FactSource
from comparison.ablation.projection import project_a, project_b
from tests.test_ablation_projection import replay
from tests.test_answer_requirements import need

ROW = 'x-claim-row'


class Source(FactSource):
    strings = {1: 'SHADOW-A', 2: 'SHADOW-B', 3: 'volume'}
    rows = {1: Fact(1, 'shadowCopy', 1000000, 0, 1, 3),
            2: Fact(2, 'shadowCopy', 2000000, 0, 2, 3)}

    def get(self, ids):
        return {i: self.rows[i] for i in ids if i in self.rows}

    def string(self, sid):
        return self.strings[sid]

    def all(self):
        return list(self.rows.values())


def candidate(cid, claim):
    return {'candidate_id': cid, 'claim': claim}


def binding(row, field, path, part=0):
    return {'candidate_id': row.get('candidate_id', row.get('finding_id')),
            'claim_sha256': claim_digest(row['claim']), 'question_id': 'Q',
            'field': field, 'path': path, 'part': part}


def public(policy=True):
    from agent.answer_requirements import KEY
    row = {'type': 'object', 'properties': {
        'id': {'type': 'string', KEY: need('shadow_copy')},
        'time': {'type': 'integer', KEY: need('recorded_timestamp_not_action_or_execution_guarantee_us')}}}
    if policy:
        row[ROW] = {'mode': 'same_claim_part'}
    return {'schema_version': 2, 'case_id': 'row-fixture', 'questions': [
        {'id': 'Q', 'prompt': 'Which shadow copies and their recorded times?',
         'answer_schema': {'type': 'object', 'properties': {
             'copies': {'type': 'array', 'items': row}}}}]}


class RowRequirements(unittest.TestCase):
    def setUp(self):
        self.source = Source()
        self.a = candidate('A', {'shadowCopyMade': [1]})
        self.b = candidate('B', {'shadowCopyMade': [2]})

    def mixed(self, a=None, b=None, prefix=None, bpart=0):
        a, b = a or self.a, b or self.b
        prefix = ['copies', 0] if prefix is None else prefix
        return [binding(a, 'shadow_copy', prefix+['id']),
                binding(b, 'recorded_time_us', prefix+['time'], bpart)]

    def assert_row_conflict(self, result):
        conflicts = [row for row in result['conflicts'] if row['reason'] == 'row_fields_require_same_claim_part']
        self.assertTrue(conflicts, result)
        self.assertEqual(conflicts[0]['question_id'], 'Q')
        self.assertEqual(set(conflicts[0]['binding_indices']), {0, 1})
        self.assertEqual(conflicts[0]['path'], ['copies', 0])
        self.assertEqual(result['submission']['answers'][0]['status'], 'unknown')

    def test_mixed_records_conflict_with_strict_mode_enabled_or_disabled(self):
        for strict in (False, True):
            result = project_answers(public(), [self.a, self.b], self.mixed(), self.source,
                                     require_claim_requirements=strict)
            self.assert_row_conflict(result)

    def test_same_compound_candidate_different_atomic_parts_conflicts(self):
        both = candidate('BOTH', {'both': [self.a['claim'], self.b['claim']]})
        result = project_answers(public(), [both], self.mixed(both, both, bpart=1), self.source)
        self.assert_row_conflict(result)

    def test_same_atomic_part_retains_values_and_legacy_without_policy_unchanged(self):
        for row in (self.a, candidate('BOTH', {'both': [self.a['claim'], self.b['claim']]})):
            result = project_answers(public(), [row], self.mixed(row, row), self.source)
            self.assertEqual(result['submission']['answers'][0]['answer'],
                             {'copies': [{'id': 'SHADOW-A', 'time': 1000000}]})
        legacy = project_answers(public(False), [self.a, self.b], self.mixed(), self.source)
        self.assertEqual(legacy['submission']['answers'][0]['answer'],
                         {'copies': [{'id': 'SHADOW-A', 'time': 2000000}]})

    def test_b_removal_cannot_reveal_frozen_conflict(self):
        a = project_a(public(), [self.a, self.b], self.mixed(), self.source)
        self.assert_row_conflict(a)
        b = project_b(a, [replay(self.a, 'verified'), replay(self.b, 'rejected')])
        self.assertEqual(b['submission'], a['submission'])
        self.assertEqual(b['conflicts'], a['conflicts'])
        self.assertEqual(b['projection'], a['projection'])

    def test_unrelated_rows_survive(self):
        bindings = self.mixed()+self.mixed(self.a, self.a, ['copies', 1])
        result = project_answers(public(), [self.a, self.b], bindings, self.source)
        self.assertTrue(result['conflicts'])
        self.assertEqual(len(result['leaves']), 2)
        self.assertTrue(all(row['binding_index'] in (2, 3) for row in result['leaves']))

    def test_nested_anyof_policy_cannot_disappear(self):
        contract = public()
        row = contract['questions'][0]['answer_schema']['properties']['copies']['items']
        contract['questions'][0]['answer_schema']['properties']['copies']['items'] = {
            'type': 'object', ROW: row.pop(ROW), 'anyOf': [row]}
        result = project_answers(contract, [self.a, self.b], self.mixed(), self.source)
        self.assert_row_conflict(result)
        branch_policy = public()
        row = branch_policy['questions'][0]['answer_schema']['properties']['copies']['items']
        branch_policy['questions'][0]['answer_schema']['properties']['copies']['items'] = {'anyOf': [row]}
        self.assert_row_conflict(project_answers(branch_policy, [self.a, self.b], self.mixed(), self.source))

    def test_unrelated_field_survives_row_conflict(self):
        from agent.answer_requirements import KEY
        contract = public()
        contract['questions'][0]['answer_schema']['properties']['unrelated'] = {'type': 'string', KEY: need('shadow_copy')}
        bindings = self.mixed()+[binding(self.a, 'shadow_copy', ['unrelated'])]
        result = project_answers(contract, [self.a, self.b], bindings, self.source)
        self.assertEqual(result['submission']['answers'][0]['answer'], {'unrelated': 'SHADOW-A'})
        self.assertEqual(len(result['leaves']), 1)

    def test_invalid_policy_fails_closed_and_preflight_is_invalid(self):
        for malformed in ({'mode': 'same_candidate'}, {'mode': 'same_claim_part', 'extra': True}, None):
            contract = public()
            row = contract['questions'][0]['answer_schema']['properties']['copies']['items']
            row[ROW] = malformed
            preflight = inspect(contract['questions'][0]['answer_schema'], catalog()['forms'], require_claim_requirements=True)
            self.assertTrue(any(item['status'] == 'invalid' for item in preflight['requirements']), preflight)
            result = project_answers(contract, [self.a], self.mixed(self.a, self.a), self.source)
            self.assertEqual(result['submission']['answers'][0]['status'], 'unknown')
        contract = public(False)
        leaf = contract['questions'][0]['answer_schema']['properties']['copies']['items']['properties']['id']
        leaf[ROW] = {'mode': 'same_claim_part'}
        preflight = inspect(contract['questions'][0]['answer_schema'], catalog()['forms'], require_claim_requirements=True)
        self.assertTrue(any(item['status'] == 'invalid' for item in preflight['requirements']))
        result = project_answers(contract, [self.a], self.mixed(self.a, self.a), self.source)
        self.assertTrue(result['unsupported'])
        self.assertFalse(any(row['path'] == ['copies', 0, 'id'] for row in result['leaves']))

    def test_different_candidates_with_identical_literals_still_conflict(self):
        duplicate = candidate('DUPLICATE', self.a['claim'])
        result = project_answers(public(), [self.a, duplicate], self.mixed(self.a, duplicate), self.source,
                                 require_claim_requirements=True)
        self.assert_row_conflict(result)

    def test_strict_missing_row_policy_fails_preflight_and_projection(self):
        contract = public(False)
        schema = contract['questions'][0]['answer_schema']
        preflight = inspect(schema, catalog()['forms'], require_claim_requirements=True)
        self.assertTrue(any(row.get('reason') == 'missing_public_claim_row_requirement'
                            and row['status'] == 'invalid' for row in preflight['requirements']), preflight)
        result = project_answers(contract, [self.a, self.b], self.mixed(), self.source,
                                 require_claim_requirements=True)
        self.assertEqual(result['submission']['answers'][0]['status'], 'unknown')
        self.assertTrue(any(row['reason'] == 'missing_public_claim_row_requirement' for row in result['unsupported']))

    def test_explicit_independent_policy_retains_separate_observations(self):
        contract = public()
        schema = contract['questions'][0]['answer_schema']
        schema['properties']['copies']['items'][ROW] = {'mode': 'independent'}
        preflight = inspect(schema, catalog()['forms'], require_claim_requirements=True)
        self.assertFalse(any(row['status'] == 'invalid' for row in preflight['requirements']), preflight)
        result = project_answers(contract, [self.a, self.b], self.mixed(), self.source,
                                 require_claim_requirements=True)
        self.assertEqual(result['submission']['answers'][0]['answer'],
                         {'copies': [{'id': 'SHADOW-A', 'time': 2000000}]})

    def test_outer_independent_does_not_supply_missing_nested_policy(self):
        contract = public(False)
        schema = contract['questions'][0]['answer_schema']
        schema[ROW] = {'mode': 'independent'}
        preflight = inspect(schema, catalog()['forms'], require_claim_requirements=True)
        missing = [row for row in preflight['requirements'] if row.get('reason') == 'missing_public_claim_row_requirement']
        self.assertTrue(missing, preflight)
        self.assertTrue(any(row['path'] == ['copies', '*'] for row in missing), missing)
        result = project_answers(contract, [self.a], self.mixed(self.a, self.a), self.source,
                                 require_claim_requirements=True)
        self.assertEqual(result['submission']['answers'][0]['status'], 'unknown')

    def test_strict_schema_valued_additional_properties_requires_own_policy(self):
        from agent.answer_requirements import KEY
        contract = public(False)
        schema = {'type': 'object', 'additionalProperties': {'type': 'string', KEY: need('shadow_copy')}}
        contract['questions'][0]['answer_schema'] = schema
        preflight = inspect(schema, catalog()['forms'], require_claim_requirements=True)
        self.assertTrue(any(row.get('reason') == 'missing_public_claim_row_requirement' for row in preflight['requirements']))
        bindings = [binding(self.a, 'shadow_copy', ['first'])]
        result = project_answers(contract, [self.a], bindings, self.source, require_claim_requirements=True)
        self.assertEqual(result['submission']['answers'][0]['status'], 'unknown')
        schema[ROW] = {'mode': 'independent'}
        allowed = project_answers(contract, [self.a], bindings, self.source, require_claim_requirements=True)
        self.assertEqual(allowed['submission']['answers'][0]['answer'], {'first': 'SHADOW-A'})

    def test_same_path_anyof_sibling_policy_satisfies_strict_row_requirement(self):
        contract = public(False)
        schema = contract['questions'][0]['answer_schema']
        row = schema['properties']['copies']['items']
        schema['properties']['copies']['items'] = {'anyOf': [row], ROW: {'mode': 'independent'}, 'type': 'object'}
        preflight = inspect(schema, catalog()['forms'], require_claim_requirements=True)
        self.assertFalse(any(row['status'] == 'invalid' for row in preflight['requirements']), preflight)
        result = project_answers(contract, [self.a, self.b], self.mixed(), self.source,
                                 require_claim_requirements=True)
        self.assertEqual(result['submission']['answers'][0]['answer'],
                         {'copies': [{'id': 'SHADOW-A', 'time': 2000000}]})

    def test_anyof_branch_policy_cannot_supply_another_branch_policy(self):
        from copy import deepcopy
        contract = public(False)
        schema = contract['questions'][0]['answer_schema']
        row = schema['properties']['copies']['items']
        declared = deepcopy(row)
        declared[ROW] = {'mode': 'independent'}
        schema['properties']['copies']['items'] = {'type': 'object', 'anyOf': [declared, row]}
        preflight = inspect(schema, catalog()['forms'], require_claim_requirements=True)
        self.assertTrue(any(item.get('reason') == 'missing_public_claim_row_requirement'
                            for item in preflight['requirements']), preflight)
        result = project_answers(contract, [self.a, self.b], self.mixed(), self.source,
                                 require_claim_requirements=True)
        self.assertEqual(result['submission']['answers'][0]['status'], 'unknown')

    def test_distributed_anyof_properties_cannot_assemble_unreviewed_row(self):
        from copy import deepcopy
        for distributed in ('common_and_branch', 'separate_alternatives'):
            with self.subTest(distributed=distributed):
                contract = public(False)
                schema = contract['questions'][0]['answer_schema']
                row = schema['properties']['copies']['items']
                identity = deepcopy(row['properties']['id'])
                stamp = deepcopy(row['properties']['time'])
                if distributed == 'common_and_branch':
                    replacement = {'type': 'object', 'properties': {'id': identity},
                                   'anyOf': [{'properties': {'time': stamp}}]}
                else:
                    # Default additionalProperties permits both keys, even
                    # though each alternative declares only one of them.
                    replacement = {'type': 'object', 'anyOf': [
                        {'properties': {'id': identity}},
                        {'properties': {'time': stamp}}]}
                schema['properties']['copies']['items'] = replacement
                preflight = inspect(schema, catalog()['forms'], require_claim_requirements=True)
                self.assertTrue(any(item.get('reason') == 'missing_public_claim_row_requirement'
                                    for item in preflight['requirements']), preflight)
                result = project_answers(contract, [self.a, self.b], self.mixed(), self.source,
                                         require_claim_requirements=True)
                self.assertEqual(result['submission']['answers'][0]['status'], 'unknown')
                self.assertTrue(any(item['reason'] == 'missing_public_claim_row_requirement'
                                    for item in result['unsupported']), result)

    def test_real_certificates_replay_but_mixed_row_remains_unknown(self):
        from checker.check import check
        from verifier.verify import verify
        with tempfile.TemporaryDirectory() as directory:
            a = check(self.a['claim'], 'A', self.source, out_dir=directory)
            b = check(self.b['claim'], 'B', self.source, out_dir=directory)
            for cert in (a, b):
                self.assertEqual(cert['status'], 'verified')
                self.assertEqual(verify(cert, self.source), [])
            mixed = project_answers(public(), [a, b], self.mixed(a, b), self.source,
                                    authority='independently_replayed')
            self.assert_row_conflict(mixed)
            correct = project_answers(public(), [a, b], self.mixed(a, a), self.source,
                                      authority='independently_replayed')
            self.assertEqual(correct['submission']['answers'][0]['answer'],
                             {'copies': [{'id': 'SHADOW-A', 'time': 1000000}]})


if __name__ == '__main__':
    unittest.main()
