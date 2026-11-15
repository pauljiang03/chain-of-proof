"""Cross-question references freeze omissions, never invent or choose a target."""
from copy import deepcopy
import unittest

from agent import answer_references as refs
from agent.answer_requirements import inspect


def reference(qid='Q28', path=None):
    return {'mode': 'same_claim_part', 'question_id': qid, 'path': ['count'] if path is None else path}


def entry(index, qid, path, candidate='C', part=0, references=None):
    return {'binding_index': index, 'question_id': qid, 'path': path, 'candidate_id': candidate,
            'part': part, 'answer_references': references or []}


def plan(entries, conflicts=None):
    return {'bindings': entries, 'frozen_conflicts': conflicts or []}


class AnswerReferences(unittest.TestCase):
    def test_target_requires_exactly_one_surviving_same_atomic_part(self):
        dependent = entry(1, 'Q29', ['deleted'], references=[reference()])
        target = entry(0, 'Q28', ['count'])
        cases = [([], 'absent'), ([dict(target, candidate_id='other')], 'different_claim_part'),
                 ([dict(target, part=1)], 'different_claim_part'),
                 ([target, dict(target, binding_index=2)], 'duplicate')]
        for targets, status in cases:
            result = refs.freeze_references(plan(targets + [deepcopy(dependent)]))
            self.assertEqual(result['frozen_conflicts'][0]['reference_status'], status)
            self.assertEqual(result['frozen_conflicts'][0]['binding_indices'], [1])
        self.assertEqual(refs.freeze_references(plan([target, dependent]))['frozen_conflicts'], [])

    def test_failed_unsupported_target_is_absent_and_conflicted_target_is_blocked(self):
        dependent = entry(1, 'Q29', ['deleted'], references=[reference()])
        document = plan([dependent]); document['unsupported'] = [{'binding_index': 0, 'question_id': 'Q28'}]
        self.assertEqual(refs.freeze_references(document)['frozen_conflicts'][0]['reference_status'], 'absent')
        document = plan([entry(0, 'Q28', ['count']), dependent], [{'binding_indices': [0], 'reason': 'row_conflict'}])
        refs.freeze_references(document)
        self.assertEqual(document['frozen_conflicts'][-1]['reference_status'], 'conflicted')

    def test_transitive_failures_propagate_without_removing_unrelated_bindings(self):
        document = plan([entry(0, 'Q1', ['a'], references=[reference('MISSING', ['x'])]),
                         entry(1, 'Q2', ['b'], references=[reference('Q1', ['a'])]),
                         entry(2, 'Q3', ['c'], references=[reference('Q2', ['b'])]),
                         entry(3, 'Q4', ['independent'])])
        refs.freeze_references(document)
        blocked = {i for conflict in document['frozen_conflicts'] for i in conflict['binding_indices']}
        self.assertEqual(blocked, {0, 1, 2})
        self.assertEqual(refs.freeze_references(document), document)  # Idempotent frozen omission.

    def test_duplicate_target_never_recovers_after_admission_filter(self):
        document = plan([entry(0, 'Q28', ['count']), entry(1, 'Q28', ['count'], candidate='D'),
                         entry(2, 'Q29', ['deleted'], references=[reference()])])
        refs.freeze_references(document)
        frozen = deepcopy(document['frozen_conflicts'])
        # B consumes already-frozen binding indices; deleting D must not unhide Q29.
        admitted = {'C'}
        blocked = {i for conflict in document['frozen_conflicts'] for i in conflict['binding_indices']}
        retained = [row for row in document['bindings'] if row['candidate_id'] in admitted and row['binding_index'] not in blocked]
        self.assertEqual([row['question_id'] for row in retained], ['Q28'])
        self.assertEqual(document['frozen_conflicts'], frozen)

    def test_public_preflight_exact_targets_dangling_self_and_cycles(self):
        def question(qid, target=None):
            leaf = {'type': 'integer'}
            if target: leaf[refs.KEY] = reference(target)
            return {'id': qid, 'answer_schema': {'type': 'object', 'properties': {'count': leaf}}}
        valid = {'questions': [question('Q28'), question('Q29', 'Q28')]}
        self.assertEqual(refs.validate_public(valid)['errors'], [])
        for questions, reason in [([question('Q29', 'Q29')], 'self_public_claim_reference'),
                ([question('Q29', 'missing')], 'dangling_public_claim_reference'),
                ([question('Q28', 'Q29'), question('Q29', 'Q28')], 'cyclic_public_claim_reference')]:
            self.assertIn(reason, [row['reason'] for row in refs.validate_public({'questions': questions})['errors']])
        valid['questions'][0]['answer_schema']['properties'] = {'other': {'type': 'integer'}}
        self.assertEqual(refs.validate_public(valid)['errors'][0]['reason'], 'dangling_public_claim_reference')

    def test_local_preflight_separate_reference_rows_and_invalid_shapes(self):
        schema = {'type': 'boolean', refs.KEY: reference()}
        view = inspect(schema, {})
        self.assertEqual(view['requirements'], [])
        self.assertEqual(len(view['reference_requirements']), 1)
        for raw in [None, {}, dict(reference(), mode='any'), dict(reference(), path=['*', -1]),
                    dict(reference(), extra=True), dict(reference(), question_id='')]:
            with self.assertRaises(ValueError): refs.parse(raw)
            self.assertEqual(inspect({'type': 'boolean', refs.KEY: raw}, {})['requirements'][0]['status'], 'invalid')
        self.assertEqual(inspect({'type': 'object', 'properties': {}, refs.KEY: reference()}, {})
                         ['requirements'][0]['reason'], 'claim_reference_must_annotate_exact_answer_value')

    def test_limits_fail_closed(self):
        with self.assertRaises(ValueError): refs.freeze_references(plan([{}] * 20001))
        with self.assertRaises(ValueError):
            refs.freeze_references(plan([entry(1, 'Q29', ['state'], references=[reference()] * 9)]))
        schema = {'properties': {str(i): {} for i in range(4097)}}
        self.assertEqual(refs.inspect_schema(schema), ([], []))
        schema['properties']['0'][refs.KEY] = reference()
        rows, errors = refs.inspect_schema(schema)
        self.assertEqual(errors[0]['reason'], 'public_claim_reference_traversal_limit')

    def test_frozen_cycles_refuse_without_recursive_self_support(self):
        document = plan([entry(0, 'Q1', ['a'], references=[reference('Q2', ['b'])]),
                         entry(1, 'Q2', ['b'], references=[reference('Q1', ['a'])]),
                         entry(2, 'Q3', ['c'], references=[reference('Q1', ['a'])])])
        refs.freeze_references(document)
        self.assertEqual({i for row in document['frozen_conflicts'] for i in row['binding_indices']}, {0, 1, 2})
        self.assertIn('cyclic', [row['reference_status'] for row in document['frozen_conflicts']])
        with self.assertRaises(ValueError):
            refs.freeze_references(plan([entry(0, 'Q1', []), entry(0, 'Q2', [])]))

    def test_duplicate_target_does_not_select_survivor_when_other_is_preblocked(self):
        document = plan([entry(0, 'Q28', ['count']), entry(1, 'Q28', ['count'], candidate='D'),
                         entry(2, 'Q29', ['deleted'], references=[reference()])],
                        [{'reason': 'prior_row_conflict', 'binding_indices': [1]}])
        refs.freeze_references(document)
        self.assertEqual(document['frozen_conflicts'][-1]['binding_indices'], [2])
        self.assertEqual(document['frozen_conflicts'][-1]['reference_status'], 'duplicate')

    def test_reference_text_value_does_not_trigger_legacy_scan(self):
        schema = {'description': 'An example {"x-claim-reference": true}',
                  'properties': {str(i): {} for i in range(4097)}}
        self.assertEqual(refs.inspect_schema(schema), ([], []))


class AnswerReferenceProjectionIntegration(unittest.TestCase):
    """Real frozen projector with in-memory reader-shaped attributes; no certificates."""
    def setUp(self):
        from checker.catalog import ROLES
        from checker.facts import Fact, FactSource
        from extractor.attributes import emit_attribute
        from extractor.store import Evidence
        evidence = Evidence()
        identities = {}
        for name, role, value in [('count', 'account.count', 2), ('other_count', 'account.count', 3),
                                  ('state', 'account.enabled', False)]:
            identities[name] = (emit_attribute(evidence, 'fixture-subject', role, value, 100000000, artifact='synthetic fixture'), role)
        strings, rows = evidence.finalize()
        class MemorySource(FactSource):
            def get(self, ids): return {fid: self.rows[fid] for fid in ids if fid in self.rows}
            def string(self, sid): return strings[sid]
        self.source = MemorySource()
        self.source.rows = {row['id']: Fact(**row) for row in rows}
        def attribute(name):
            identity, role = identities[name]
            fields = {row.kind: row.id for row in self.source.rows.values() if strings[row.obj] == identity}
            return [fields['attributeSubject'], fields[ROLES[role].kind], fields[ROLES[role].value_kind], role]
        self.first = {'attributeTuple': [attribute('count'), attribute('state')]}
        self.second = {'attributeTuple': [attribute('other_count'), attribute('state')]}
        self.candidates = [{'candidate_id': 'C', 'claim': self.first}, {'candidate_id': 'D', 'claim': self.second}]
        self.public = {'schema_version': 2, 'case_id': 'reference-fixture', 'questions': []}
        for qid, field, role, kind in [('Q28', 'count', 'account.count', 'integer'),
                                       ('Q29', 'deleted', 'account.enabled', 'boolean')]:
            leaf = {'type': kind, 'x-claim-requirement': {
                'semantic_types': [ROLES[role].semantic_type], 'meaning': 'Synthetic recorded attribute.',
                'evidence_needed': 'Exact native typed fixture value from this atomic tuple.'}}
            if qid == 'Q29': leaf[refs.KEY] = reference()
            self.public['questions'].append({'id': qid, 'prompt': 'Synthetic dependency fixture.',
                'answer_schema': {'type': 'object', 'properties': {field: leaf},
                    'x-claim-scope': {'mode': 'unscoped_observation', 'meaning': 'Synthetic guard mechanics only.'}}})

    def binding(self, cid, qid, field, path, part=0, **extra):
        from agent.answer_projection import claim_digest
        candidate = next(row for row in self.candidates if row['candidate_id'] == cid)
        return {'candidate_id': cid, 'question_id': qid, 'field': field, 'path': path, 'part': part,
                'claim_sha256': claim_digest(candidate['claim']), **extra}

    def project(self, bindings):
        from agent.answer_projection import project_answers
        return project_answers(self.public, self.candidates, bindings, self.source,
                               require_claim_requirements=True, require_evidence_scope=True)

    def target(self, cid='C', **extra):
        return self.binding(cid, 'Q28', 'value_0', ['count'], **extra)

    def dependent(self, **extra):
        return self.binding('C', 'Q29', 'value_1', ['deleted'], **extra)

    def test_projector_same_tuple_accepts_and_b_replays_without_source_access(self):
        from agent.answer_projection import render_projection
        result = self.project([self.target(), self.dependent()])
        self.assertEqual(result['submission']['answers'][1]['answer'], {'deleted': False})
        self.assertEqual(result['projection']['bindings'][1]['answer_references'], [reference()])
        self.source.get = lambda ids: self.fail('Frozen B replay must not re-open evidence')
        replayed = render_projection(result['projection'], admitted_ids=['C'], authority='independently_replayed')
        self.assertEqual(replayed['submission'], result['submission'])
        filtered = render_projection(result['projection'], admitted_ids=['D'])
        self.assertEqual([row['status'] for row in filtered['submission']['answers']], ['unknown', 'unknown'])

    def test_omitted_and_unsupported_target_freeze_dependent(self):
        for bindings in [[self.dependent()], [self.target(value=99), self.dependent()]]:
            result = self.project(bindings)
            self.assertEqual(result['submission']['answers'][1]['status'], 'unknown')
            self.assertEqual(result['conflicts'][-1]['reference_status'], 'absent')
        result = self.project([self.target(value=99), self.dependent()])
        self.assertEqual(result['unsupported'][0]['reason'], 'literal_value_mismatch_not_repaired')

    def test_duplicate_and_conflicting_target_cannot_switch_after_b_filter(self):
        from agent.answer_projection import render_projection
        for target in [self.target(), self.target('D')]:
            result = self.project([self.target(), target, self.dependent()])
            self.assertEqual(result['submission']['answers'][1]['status'], 'unknown')
            self.assertIn('duplicate', [row.get('reference_status') for row in result['conflicts']])
            # D removal cannot turn the original ambiguous target choice into C.
            replayed = render_projection(result['projection'], admitted_ids=['C'])
            self.assertEqual(replayed['submission']['answers'][1]['status'], 'unknown')
            self.assertEqual(replayed['conflicts'], result['conflicts'])

    def test_foreign_candidate_or_other_both_part_cannot_supply_reference(self):
        result = self.project([self.target('D'), self.dependent()])
        self.assertEqual(result['conflicts'][-1]['reference_status'], 'different_claim_part')
        self.candidates[0]['claim'] = {'both': [self.first, self.second]}
        result = self.project([self.target(), self.dependent(part=1)])
        self.assertEqual(result['submission']['answers'][1]['status'], 'unknown')
        self.assertEqual(result['conflicts'][-1]['reference_status'], 'different_claim_part')

    def test_invalid_public_reference_refuses_before_source_or_candidate_processing(self):
        self.public['questions'][1]['answer_schema']['properties']['deleted'][refs.KEY]['question_id'] = 'missing'
        self.source.get = lambda ids: self.fail('Invalid public references must refuse before evidence access')
        with self.assertRaisesRegex(ValueError, 'invalid_public_claim_references'):
            self.project([self.target(), self.dependent()])

    def test_single_target_in_a_frozen_row_conflict_blocks_dependent_after_b_removal(self):
        from agent.answer_projection import render_projection
        schema = self.public['questions'][0]['answer_schema']
        schema['x-claim-row'] = {'mode': 'same_claim_part'}
        other = deepcopy(self.public['questions'][1]['answer_schema']['properties']['deleted'])
        other.pop(refs.KEY)
        schema['properties']['other'] = other
        foreign = self.binding('D', 'Q28', 'value_1', ['other'])
        result = self.project([self.target(), foreign, self.dependent()])
        self.assertEqual(result['submission']['answers'][0]['status'], 'unknown')
        self.assertEqual(result['submission']['answers'][1]['status'], 'unknown')
        self.assertIn('conflicted', [row.get('reference_status') for row in result['conflicts']])
        replayed = render_projection(result['projection'], admitted_ids=['C'])
        self.assertEqual(replayed['submission'], result['submission'])
        self.assertEqual(replayed['conflicts'], result['conflicts'])

    def array_contract(self, path=None, nested=False):
        leaf = deepcopy(self.public['questions'][0]['answer_schema']['properties']['count'])
        scope = {'mode': 'unscoped_observation', 'meaning': 'Synthetic array reference mechanics.'}
        schema = {'type': 'array', 'items': leaf, 'x-claim-scope': scope}
        if nested:
            schema = {'type': 'object', 'properties': {'groups': {
                'type': 'array', 'items': {'type': 'array', 'items': leaf}}}, 'x-claim-scope': scope}
        self.public['questions'][0]['answer_schema'] = schema
        self.public['questions'][1]['answer_schema']['properties']['deleted'][refs.KEY] = reference(
            path=[1] if path is None else path)

    def test_sparse_array_target_moves_but_dependent_is_frozen_out(self):
        from agent.answer_projection import render_projection
        self.array_contract()
        target = self.binding('C', 'Q28', 'value_0', [1])
        result = self.project([target, self.dependent()])
        self.assertEqual(result['submission']['answers'][0]['answer'], [2])
        self.assertEqual(result['submission']['answers'][1]['status'], 'unknown')
        conflict = result['conflicts'][-1]
        self.assertEqual(conflict['reference_status'], 'target_output_path_changed')
        self.assertEqual((conflict['target_path'], conflict['target_output_path']), ([1], [0]))
        self.assertEqual(result['leaves'][0]['path'], [1])
        self.assertEqual(result['leaves'][0]['output_path'], [0])
        replayed = render_projection(result['projection'], admitted_ids=['C'])
        self.assertEqual(replayed['submission'], result['submission'])
        self.assertEqual(replayed['conflicts'], result['conflicts'])

    def test_dense_array_reference_survives_until_b_removes_a_preceding_row(self):
        from agent.answer_projection import render_projection
        self.array_contract()
        prior = self.binding('D', 'Q28', 'value_0', [0])
        target = self.binding('C', 'Q28', 'value_0', [1])
        a = self.project([prior, target, self.dependent()])
        self.assertEqual(a['submission']['answers'][0]['answer'], [3, 2])
        self.assertEqual(a['submission']['answers'][1]['answer'], {'deleted': False})
        self.assertEqual(a['conflicts'], [])
        self.source.get = lambda ids: self.fail('B must not reopen evidence to validate output paths')
        self.assertEqual(render_projection(a['projection'], admitted_ids=['C', 'D'],
                                           authority='recorded_certificates')['submission'], a['submission'])
        b = render_projection(a['projection'], admitted_ids=['C'], authority='recorded_certificates')
        self.assertEqual(b['submission']['answers'][0]['answer'], [2])
        self.assertEqual(b['submission']['answers'][1]['status'], 'unknown')
        self.assertEqual(b['conflicts'][-1]['reference_status'], 'target_output_path_changed')
        self.assertEqual(b['dropped'][-1]['reason'], 'answer_reference_output_conflict')
        self.assertTrue(b['dropped'][-1]['candidate_admitted'])

    def test_nested_array_paths_use_final_addresses_and_preserve_dense_observations(self):
        from agent.answer_projection import render_projection
        path = ['groups', 1, 2]
        self.array_contract(path, nested=True)
        target = self.binding('C', 'Q28', 'value_0', path)
        sparse = self.project([target, self.dependent()])
        self.assertEqual(sparse['submission']['answers'][0]['answer'], {'groups': [[2]]})
        self.assertEqual(sparse['conflicts'][-1]['target_output_path'], ['groups', 0, 0])
        self.assertEqual(sparse['submission']['answers'][1]['status'], 'unknown')
        prior = [self.binding('D', 'Q28', 'value_0', ['groups']+indices)
                 for indices in ([0, 0], [1, 0], [1, 1])]
        dense = self.project(prior+[target, self.dependent()])
        self.assertEqual(dense['submission']['answers'][0]['answer'], {'groups': [[3], [3, 3, 2]]})
        self.assertEqual(dense['submission']['answers'][1]['answer'], {'deleted': False})
        filtered = render_projection(dense['projection'], admitted_ids=['C'])
        self.assertEqual(filtered['submission']['answers'][0]['answer'], {'groups': [[2]]})
        self.assertEqual(filtered['submission']['answers'][1]['status'], 'unknown')

    def test_output_reference_failures_propagate_in_dependency_order_only(self):
        from agent.answer_projection import render_projection
        self.array_contract()
        state = deepcopy(self.public['questions'][1]['answer_schema']['properties']['deleted'])
        state[refs.KEY] = reference('Q29', ['deleted'])
        state['x-claim-scope'] = {'mode': 'unscoped_observation', 'meaning': 'Synthetic chained dependency.'}
        # Deliberately place the dependent before its target in public order.
        self.public['questions'].insert(0, {'id': 'Q30', 'prompt': 'Dependent observation.', 'answer_schema': state})
        independent = deepcopy(self.public['questions'][1]['answer_schema']['items'])
        independent['x-claim-scope'] = {'mode': 'unscoped_observation', 'meaning': 'Synthetic independent observation.'}
        self.public['questions'].append({'id': 'Q40', 'prompt': 'Independent observation.', 'answer_schema': independent})
        result = self.project([self.binding('C', 'Q28', 'value_0', [1]), self.dependent(),
                               self.binding('C', 'Q30', 'value_1', []),
                               self.binding('C', 'Q40', 'value_0', [])])
        answers = {row['question_id']: row for row in result['submission']['answers']}
        self.assertEqual(answers['Q28']['answer'], [2])
        self.assertEqual(answers['Q40']['answer'], 2)
        self.assertEqual(answers['Q29']['status'], 'unknown')
        self.assertEqual(answers['Q30']['status'], 'unknown')
        failures = {row['question_id']: row['reference_status'] for row in result['conflicts']}
        self.assertEqual(failures, {'Q29': 'target_output_path_changed', 'Q30': 'target_not_retained'})
        dense = self.project([self.binding('D', 'Q28', 'value_0', [0]),
                              self.binding('C', 'Q28', 'value_0', [1]), self.dependent(),
                              self.binding('C', 'Q30', 'value_1', []),
                              self.binding('C', 'Q40', 'value_0', [])])
        self.assertTrue(all(row['status'] == 'answered' for row in dense['submission']['answers']))
        self.source.get = lambda ids: self.fail('Transitive output validation must use frozen values only')
        filtered = render_projection(dense['projection'], admitted_ids=['C'])
        self.assertEqual(filtered['submission'], result['submission'])
        self.assertEqual({row['question_id']: row['reference_status'] for row in filtered['conflicts']}, failures)

    def test_conflicted_preceding_row_cannot_silently_shift_reference_target(self):
        self.array_contract()
        result = self.project([self.binding('C', 'Q28', 'value_0', [0]),
                               self.binding('D', 'Q28', 'value_0', [0]),
                               self.binding('C', 'Q28', 'value_0', [1]), self.dependent()])
        self.assertEqual(result['submission']['answers'][0]['answer'], [2])
        self.assertEqual(result['submission']['answers'][1]['status'], 'unknown')
        self.assertIn('target_output_path_changed', [row.get('reference_status') for row in result['conflicts']])
