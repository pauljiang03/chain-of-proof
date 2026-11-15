"""Reference/address invariants over all 810 small scenarios, checked by a rank-based oracle.

Each of five indices is absent, rejected or admitted (the target is never absent); the
oracle uses only sorted ranks and authored coordinates, never the assembly code.
"""
from copy import deepcopy
import unittest

from agent.answer_projection import claim_digest, prepare_projection, render_projection
from checker.catalog import ROLES
from checker.facts import Fact, FactSource
from comparison.ablation.projection import project_b
from extractor.attributes import emit_attribute
from extractor.store import Evidence

INDICES = tuple(range(5))


def subsets(values):
    return (tuple(value for index, value in enumerate(values) if mask & (1 << index))
            for mask in range(1 << len(values)))


def oracle(authored, admitted, target):
    # Only rank in an ordered finite set defines the emitted array coordinate.
    authored_order = sorted(authored)
    admitted_order = sorted(set(authored) & set(admitted))
    valid_in_a = target in authored_order and authored_order.index(target) == target
    dependent = (valid_in_a and target in admitted_order and admitted_order.index(target) == target)
    return [100 + index for index in admitted_order], dependent


class AnswerReferenceInvariants(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        evidence, identities = Evidence(), {}
        for index in INDICES:
            for name, role, value in [('literal', 'account.count', 100 + index),
                                      ('dependent', 'account.enabled', False)]:
                identities[index, name] = (emit_attribute(evidence, 'synthetic-subject-' + str(index),
                    role, value, 100000000, artifact='synthetic invariant fixture'), role)
        strings, raw = evidence.finalize()
        class MemorySource(FactSource):
            def get(self, ids): return {fid: self.rows[fid] for fid in ids if fid in self.rows}
            def string(self, sid): return strings[sid]
            def all(self): raise AssertionError('Attribute fixture must not enumerate unrelated evidence')
        cls.source = MemorySource()
        cls.source.rows = {row['id']: Fact(**row) for row in raw}
        def attribute(index, name):
            identity, role = identities[index, name]
            rows = {row.kind: row.id for row in cls.source.rows.values() if strings[row.obj] == identity}
            return [rows['attributeSubject'], rows[ROLES[role].kind], rows[ROLES[role].value_kind], role]
        cls.candidates = [{'candidate_id': 'C' + str(index), 'claim': {'attributeTuple': [
            attribute(index, 'literal'), attribute(index, 'dependent')]}} for index in INDICES]

    def public(self, target):
        def leaf(role, kind):
            return {'type': kind, 'x-claim-requirement': {
                'semantic_types': [ROLES[role].semantic_type], 'meaning': 'Synthetic native typed value.',
                'evidence_needed': 'A source-backed atomic tuple; this is a guard invariant fixture.'}}
        array_leaf = leaf('account.count', 'integer')
        dependent = leaf('account.enabled', 'boolean')
        dependent['x-claim-reference'] = {'mode': 'same_claim_part', 'question_id': 'Q1', 'path': [target]}
        scope = {'mode': 'unscoped_observation', 'meaning': 'Synthetic rank invariants only, no forensic relevance.'}
        return {'schema_version': 2, 'case_id': 'generated-reference-ranks', 'questions': [
            {'id': 'Q1', 'prompt': 'Independent literal observations.', 'answer_schema': {
                'type': 'array', 'items': array_leaf, 'x-claim-scope': scope}},
            {'id': 'Q2', 'prompt': 'Dependent observation referencing an exact public index.',
             'answer_schema': dict(dependent, **{'x-claim-scope': scope})}]}

    def prepare(self, authored, target, ordering=None):
        bindings = []
        for index in authored:
            candidate = self.candidates[index]
            bindings.append({'candidate_id': candidate['candidate_id'], 'claim_sha256': claim_digest(candidate['claim']),
                             'question_id': 'Q1', 'path': [index], 'part': 0, 'field': 'value_0'})
        candidate = self.candidates[target]
        bindings.append({'candidate_id': candidate['candidate_id'], 'claim_sha256': claim_digest(candidate['claim']),
                         'question_id': 'Q2', 'path': [], 'part': 0, 'field': 'value_1'})
        if ordering == 'reverse': bindings.reverse()
        elif ordering == 'dependent_first': bindings = bindings[-1:] + bindings[:-1]
        return prepare_projection(self.public(target), self.candidates, bindings, self.source,
                                  require_claim_requirements=True, require_evidence_scope=True)

    def assert_oracle(self, result, authored, admitted, target):
        literals, dependent = oracle(authored, admitted, target)
        answers = {row['question_id']: row for row in result['submission']['answers']}
        if literals:
            self.assertEqual(answers['Q1']['answer'], literals)
        else:
            self.assertEqual(answers['Q1']['status'], 'unknown')
        if dependent:
            self.assertIs(answers['Q2']['answer'], False)
            target_leaf = next(row for row in result['leaves'] if row['question_id'] == 'Q1' and row['path'] == [target])
            self.assertEqual(target_leaf['output_path'], [target])
            dependent_leaf = next(row for row in result['leaves'] if row['question_id'] == 'Q2')
            self.assertEqual((dependent_leaf['candidate_id'], dependent_leaf['part']),
                             (target_leaf['candidate_id'], target_leaf['part']))
        else:
            self.assertEqual(answers['Q2']['status'], 'unknown')
        self.assertEqual(len([leaf for leaf in result['leaves'] if leaf['question_id'] == 'Q1']), len(literals))

    def test_all_810_authored_admitted_scenarios_and_admission_order(self):
        scenarios = 0
        for target in INDICES:
            others = tuple(index for index in INDICES if index != target)
            for authored_others in subsets(others):
                authored = tuple(sorted(authored_others + (target,)))
                plan = self.prepare(authored, target)
                original_hash = plan['projection_sha256']
                original_conflicts = deepcopy(plan['frozen_conflicts'])
                dependent_index = next(row['binding_index'] for row in plan['bindings'] if row['question_id'] == 'Q2')
                frozen_indices = {index for row in original_conflicts for index in row['binding_indices']}
                self.assertEqual(dependent_index in frozen_indices, not oracle(authored, authored, target)[1])
                for admitted in subsets(authored):
                    with self.subTest(target=target, authored=authored, admitted=admitted):
                        ids = ['C' + str(index) for index in admitted]
                        forward = render_projection(plan, admitted_ids=ids)
                        backward = render_projection(plan, admitted_ids=list(reversed(ids)))
                        self.assert_oracle(forward, authored, admitted, target)
                        self.assertEqual(forward['submission'], backward['submission'])
                        self.assertEqual(forward['conflicts'], backward['conflicts'])
                        self.assertEqual(plan['projection_sha256'], original_hash)
                        self.assertEqual(plan['frozen_conflicts'], original_conflicts)
                    scenarios += 1
        self.assertEqual(scenarios, 810)

    def test_binding_permutations_preserve_sparse_and_dense_meanings(self):
        authored_sets = ((0, 1, 2, 3, 4), (0, 2, 4), (1, 3), (4,))
        for authored in authored_sets:
            for target in authored:
                plans = [self.prepare(authored, target, ordering) for ordering in (None, 'reverse', 'dependent_first')]
                for admitted in (authored, (target,), (), tuple(index for index in authored if index != min(authored))):
                    submissions = []
                    for plan in plans:
                        result = render_projection(plan, admitted_ids=['C' + str(index) for index in admitted])
                        self.assert_oracle(result, authored, admitted, target)
                        submissions.append(result['submission'])
                    self.assertEqual(submissions[0], submissions[1])
                    self.assertEqual(submissions[0], submissions[2])

    def test_b_adapter_preserves_frozen_and_newly_shifted_refusals(self):
        for authored, target, admitted in [((0, 1, 2, 3, 4), 2, (1, 2, 3, 4)),
                                          ((0, 2, 4), 4, (4,)),
                                          ((0, 1, 2), 2, (0, 1, 2)),
                                          ((0,), 0, ())]:
            plan = self.prepare(authored, target)
            a = dict(render_projection(plan), arm='A', projection=plan)
            rows = [dict(candidate, status='verified' if index in admitted else 'rejected',
                         checker_status='verified' if index in admitted else 'rejected',
                         verification={'passed': True} if index in admitted else None)
                    for index, candidate in enumerate(self.candidates)]
            b = project_b(a, rows)
            self.assert_oracle(b, authored, admitted, target)
            self.assertEqual(b['projection'], plan)
            self.assertFalse(b['source_repair'])
            self.assertEqual(b['model_calls'], 0)
