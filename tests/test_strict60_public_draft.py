"""Public-only contract fidelity and refusal regressions; no benchmark answers."""
from collections import Counter
import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from agent.answer_projection import catalog, claim_digest, project_answers
from agent.answer_requirements import inspect
from agent.case import read_question_profile
from tests.test_answer_requirements import Source
from eval.data_leakage_strict_draft.scope_contract import apply_hacking_scopes

ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / 'eval/data_leakage_strict_draft'
spec = importlib.util.spec_from_file_location('strict60_assemble', DRAFT / 'assemble.py')
assembly = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assembly)


class StrictPublicDraft(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.public = read_question_profile(DRAFT / 'questions.json')

    def test_original_prompts_schemas_and_matching_rules_preserved(self):
        original = read_question_profile(ROOT / 'eval/benchmark_nist_questions.json')
        self.assertNotEqual(self.public['case_id'], original['case_id'])
        self.assertEqual(assembly.without_annotations(self.public['questions']), original['questions'])
        self.assertEqual([q['id'] for q in self.public['questions']], [f'Q{i}' for i in range(1, 61)])

    def test_public_derivatives_reproduce_and_remain_blocked(self):
        outputs = assembly.build()
        for name, value in outputs.items():
            recorded = json.loads((DRAFT / name).read_text())
            if name == 'review.json':
                # Source hashes identify the reviewed revision. Later unrelated
                # code edits must not rewrite that historical receipt. Current
                # catalog compatibility and every public authoring input still
                # have to reproduce the recorded field decisions below.
                old_inputs = {row['path']: row for row in recorded['original_inputs']}
                for index, row in enumerate(value['original_inputs']):
                    if row['path'].startswith(('agent/', 'checker/')):
                        self.assertEqual(len(old_inputs[row['path']]['sha256']), 64)
                        value['original_inputs'][index] = old_inputs[row['path']]
            self.assertEqual(recorded, value)
        report = outputs['review.json']
        self.assertFalse(report['model_run_ready'])
        self.assertEqual(len(report['launch_blockers']), 4)
        self.assertEqual(report['counts']['leaf_occurrences_including_anyof_branches'], 358)
        self.assertEqual(report['counts']['catalog_supported'], 55)
        self.assertEqual(report['counts']['explicitly_unsupported'], 303)
        self.assertEqual(report['counts']['row_policies'], 93)

    def test_every_declared_leaf_has_valid_explicit_support_or_gap(self):
        counts = Counter()
        for question in self.public['questions']:
            preflight = inspect(question['answer_schema'], catalog()['forms'], require_claim_requirements=True, require_evidence_scope=True)
            self.assertTrue(preflight['scope_requirements'])
            self.assertTrue(all(row['status'] in ('valid', 'unavailable') for row in preflight['scope_requirements']))
            rows = preflight['requirements']
            for row in rows:
                counts[row['status']] += 1
                self.assertIn(row['status'], ('catalog_support', 'no_catalog_support'))
                requirement = row['requirement']
                if row['status'] == 'catalog_support':
                    self.assertTrue(requirement.get('selectors'))
                    self.assertTrue(row['available_fields'])
                else:
                    self.assertTrue(all(name.startswith('needs_') for name in requirement['semantic_types']))
        self.assertEqual(counts, {'catalog_support': 55, 'no_catalog_support': 303})

    def test_reviewed_execution_path_supplies_partial_without_inventing_time(self):
        from checker.check import check
        from checker.catalog import ROLES
        from checker.facts import JsonFacts
        from extractor.attributes import emit_attribute
        from extractor.store import Evidence
        from verifier.verify import verify
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = Evidence()
            role = 'app.execution.path'
            identity = emit_attribute(evidence, 'synthetic-image:UserAssist-entry:42', role,
                                      r'C:\Synthetic\recorded.exe', 1000000,
                                      artifact='synthetic reviewed execution artifact',
                                      image='pc.E01', exhibit='PC', source_snapshot='base-volume', source_variant='primary')
            source_role = 'app.execution.source_type'
            source_identity = emit_attribute(evidence, 'synthetic-image:UserAssist-entry:42', source_role,
                                      'UserAssist', 1000000,
                                      artifact='synthetic reviewed execution artifact',
                                      image='pc.E01', exhibit='PC', source_snapshot='base-volume', source_variant='primary')
            evidence.write_json(root / 'facts.json', {})
            source = JsonFacts(root / 'facts.json')
            rows = {row.kind: row.id for row in source.all() if source.string(row.obj) == identity}
            family = {row.kind: row.id for row in source.all() if source.string(row.obj) == source_identity}
            claim = {'attributeTuple': [[rows['attributeSubject'], rows[ROLES[role].kind], rows['attributeTextValue'], role],
                                       [family['attributeSubject'], family[ROLES[source_role].kind], family['attributeTextValue'], source_role]]}
            certificate = check(claim, 'Execution', source, out_dir=root)
            self.assertEqual(certificate['status'], 'verified')
            self.assertEqual(verify(certificate, source), [])
            bindings = [{'candidate_id': 'Execution', 'claim_sha256': claim_digest(claim),
                         'question_id': 'Q11', 'path': ['records', 0, 'path_or_application_id'], 'field': 'value_0'}]
            result = project_answers(self.public, [certificate], bindings, source,
                                     require_claim_requirements=True, require_evidence_scope=True,
                                     evidence_facts_sha256=hashlib.sha256((root / 'facts.json').read_bytes()).hexdigest(),
                                     authority='recorded_certificates')
            answer = next(row for row in result['submission']['answers'] if row['question_id'] == 'Q11')
            self.assertEqual(answer['answer'], {'records': [{'path_or_application_id': r'C:\Synthetic\recorded.exe'}]})
            self.assertFalse(result['unsupported'])

    def test_generic_observations_cannot_supply_three_known_stronger_answers(self):
        source = Source()
        for row in source.rows.values():
            row.prov.update(image='pc.E01', exhibit='PC', source_snapshot='base-volume', source_variant='primary')
        candidates = [{'candidate_id': 'Program', 'claim': {'programRan': [1]}},
                      {'candidate_id': 'Suffix', 'claim': {'journalPathAt': [2]}},
                      {'candidate_id': 'Removal', 'claim': {'fileRemovedAt': [3]}}]
        targets = [('Q18', ['application'], 'program'), ('Q34', ['paths', 0], 'path_or_incomplete_suffix'),
                   ('Q52', ['actions', 0, 'action'], 'record_kind')]
        bindings = [{'candidate_id': candidate['candidate_id'], 'claim_sha256': claim_digest(candidate['claim']),
                     'question_id': qid, 'path': path, 'field': field}
                    for candidate, (qid, path, field) in zip(candidates, targets)]
        output = project_answers(self.public, candidates, bindings, source, require_claim_requirements=True,
                                 require_evidence_scope=True, evidence_facts_sha256='a' * 64)
        self.assertEqual(output['leaves'], [])
        self.assertEqual([row['reason'] for row in output['unsupported']],
                         ['claim_role_does_not_meet_public_requirement'] * 3)

    def test_additional_properties_cannot_bypass_missing_meaning(self):
        candidate = {'candidate_id': 'Program', 'claim': {'programRan': [1]}}
        bindings = [{'candidate_id': 'Program', 'claim_sha256': claim_digest(candidate['claim']),
                     'question_id': q['id'], 'path': ['unreviewed_extra'], 'field': 'program'}
                    for q in self.public['questions']]
        output = project_answers(self.public, [candidate], bindings, Source(), require_claim_requirements=True)
        self.assertEqual(output['leaves'], [])
        self.assertEqual(len(output['unsupported']), 60)

    def test_hacking_derivative_preserves_public_shape_and_remains_held(self):
        directory = ROOT / 'eval/hacking_case_strict_draft'
        original = read_question_profile(ROOT / 'eval/hacking_case/questions.json')
        draft = read_question_profile(directory / 'questions.json')
        report = json.loads((directory / 'review.json').read_text())
        self.assertNotEqual(draft['case_id'], original['case_id'])
        self.assertEqual(assembly.without_annotations(draft['questions']),
                         assembly.without_annotations(original['questions']))
        counts, policies = Counter(), []
        for question in draft['questions']:
            preflight = inspect(question['answer_schema'], catalog()['forms'], require_claim_requirements=True, require_evidence_scope=True)
            counts.update(row['status'] for row in preflight['requirements'])
            policies.extend(preflight['row_requirements'])
            self.assertTrue(all(row['status'] == 'valid' for row in preflight['scope_requirements']))
        self.assertEqual(counts, {'catalog_support': 14, 'no_catalog_support': 24})
        self.assertEqual(len(policies), 32)
        self.assertFalse(report['model_run_ready'])
        # Reapplying the reviewed public plan must be idempotent, including the
        # scan input origin and two image-integrity component origins.
        apply_hacking_scopes(draft['questions'], json.loads((directory / 'scope_plan.json').read_text()))
        self.assertEqual(draft, read_question_profile(directory / 'questions.json'))

    def test_historical_and_reconstruction_sources_remain_explicitly_unavailable(self):
        for qid in ('Q48', 'Q49', 'Q55', 'Q56', 'Q57'):
            schema = next(q['answer_schema'] for q in self.public['questions'] if q['id'] == qid)
            policies = inspect(schema, catalog()['forms'], require_claim_requirements=True,
                               require_evidence_scope=True)['scope_requirements']
            self.assertTrue(any(row['status'] == 'unavailable' for row in policies), qid)


if __name__ == '__main__':
    unittest.main()
