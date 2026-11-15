"""Verified observations cannot fill stronger fields without declared role support."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from agent import answer_requirements as requirements
from agent.answer_projection import catalog, claim_digest, project_answers, render_projection
from agent.answer_store import answer, project_bundle
from agent.investigation import Investigation
from checker import check, export, report
from checker.facts import Fact, FactSource
from verifier.verify import verify


def need(semantic_type, selectors=None):
    value = {'semantic_types': [semantic_type], 'meaning': 'The explicitly requested meaning.',
             'evidence_needed': 'A source-linked claim with this meaning; keep weaker observations separate.'}
    if selectors is not None:
        value['selectors'] = selectors
    return value


def public(typed=True):
    meanings = {'MAIL': 'email_application_product_with_version',
                'COPY': 'complete_copy_destination_path', 'PURPOSE': 'anti_forensic_action'}
    return {'schema_version': 2, 'case_id': 'synthetic-meaning-case', 'questions': [
        {'id': qid, 'prompt': 'Public request for ' + qid, 'answer_schema': {
            'type': 'string', **({requirements.KEY: need(kind)} if typed else {})}}
        for qid, kind in meanings.items()]}


class Source(FactSource):
    def __init__(self):
        self.strings = {1: 'POSTBOX.EXE', 2: 'C:\\Apps\\POSTBOX.EXE',
                        3: '[unresolved ancestor]\\staging\\draft.txt', 4: 'scoped-file-id',
                        5: 'cache.db-wal', 6: 'volume-1', 7: 'DEVICE-Z', 8: 'PC',
                        9: 'Postbox Product', 10: '7.2'}
        self.rows = {row.id: row for row in [
            Fact(1, 'programRun', 123000000, 1, 1, 2, {'artifact': 'synthetic prefetch'}),
            Fact(2, 'journalPath', 124000000, 1, 3, 4, {'path_complete': False}),
            Fact(3, 'fileRemoved', 125000000, 1, 5, 6, {'time_meaning': 'retained flag observation'}),
            Fact(4, 'usbInsert', 126000000, 1, 7, 8),
            Fact(5, 'programInstalled', 127000000, 1, 9, 10)]}

    def get(self, ids):
        return {i: self.rows[i] for i in ids if i in self.rows}

    def string(self, sid):
        return self.strings[sid]

    def all(self):
        return list(self.rows.values())


def binding(candidate, qid, field, path=None, **extra):
    return {'candidate_id': candidate['finding_id'], 'claim_sha256': claim_digest(candidate['claim']),
            'question_id': qid, 'part': 0, 'field': field, 'path': [] if path is None else path, **extra}


class AnswerRequirements(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.saved.cleanup)
        cls.source = Source()
        cls.certs = [check.check({form: [fid]}, 'F' + str(fid), cls.source, out_dir=cls.saved.name)
                     for fid, form in [(1, 'programRan'), (2, 'journalPathAt'), (3, 'fileRemovedAt'),
                                       (4, 'usbConnected'), (5, 'programInstalledAt')]]
        for cert in cls.certs:
            if cert['status'] != 'verified':
                raise AssertionError(cert)
        cls.bindings = [binding(cls.certs[0], 'MAIL', 'program'),
                        binding(cls.certs[1], 'COPY', 'path_or_incomplete_suffix'),
                        binding(cls.certs[2], 'PURPOSE', 'record_kind')]

    def project(self, contract, bindings=None, candidates=None):
        return project_answers(contract, candidates or self.certs, bindings or self.bindings,
                               self.source, authority='recorded_certificates')

    def test_reproduces_three_verified_but_overstated_answers_without_requirements(self):
        for cert in self.certs[:3]:
            self.assertEqual(cert['axioms'], [])
            self.assertEqual(verify(cert, self.source), [])
        result = self.project(public(False))
        self.assertEqual([row['answer'] for row in result['submission']['answers']],
                         ['POSTBOX.EXE', '[unresolved ancestor]\\staging\\draft.txt', 'fileRemoved'])
        self.assertEqual(result['certification'], 'not_performed_by_projector')

    def test_explicit_roles_block_all_three_without_changing_claims_or_values(self):
        original = deepcopy(self.certs)
        result = self.project(public())
        self.assertEqual([row['status'] for row in result['submission']['answers']], ['unknown'] * 3)
        self.assertEqual([row['reason'] for row in result['unsupported']],
                         ['claim_role_does_not_meet_public_requirement'] * 3)
        self.assertEqual(self.certs, original)
        self.assertEqual(result['unsupported'][0]['meaning_checks'][0]['offered']['semantic_type'], 'program')
        self.assertIn('source-linked claim', result['unsupported'][0]['meaning_checks'][0]['requirement']['evidence_needed'])

    def test_supported_sibling_and_narrow_observation_are_preserved(self):
        contract = public()
        contract['questions'][0]['answer_schema'] = {'type': 'object', 'properties': {
            'product': {'type': 'string', requirements.KEY: need('email_application_product_with_version')},
            'observed_executable': {'type': 'string', requirements.KEY: need('program',
                [{'form': 'programRan', 'field': 'program'}])}}}
        result = self.project(contract, [binding(self.certs[0], 'MAIL', 'program', ['product']),
                                         binding(self.certs[0], 'MAIL', 'program', ['observed_executable'])])
        self.assertEqual(result['submission']['answers'][0]['answer'], {'observed_executable': 'POSTBOX.EXE'})
        self.assertEqual(result['leaves'][0]['meaning_checks'][0]['status'], 'compatible')
        self.assertEqual(result['question_completeness'], 'not_established')

    def test_selector_distinguishes_forms_that_share_the_same_semantic_type(self):
        contract = public()
        contract['questions'][0]['answer_schema'][requirements.KEY] = need('program',
            [{'form': 'programInstalledAt', 'field': 'program'}])
        rejected = self.project(contract, [self.bindings[0]])
        self.assertEqual(rejected['submission']['answers'][0]['status'], 'unknown')
        accepted = self.project(contract, [binding(self.certs[4], 'MAIL', 'program')])
        self.assertEqual(accepted['submission']['answers'][0]['answer'], 'Postbox Product')

    def test_formatting_cannot_upgrade_a_recorded_timestamp_to_an_action_time(self):
        contract = public()
        contract['questions'][2]['answer_schema'][requirements.KEY] = need('anti_forensic_action_time_us')
        result = self.project(contract, [binding(self.certs[2], 'PURPOSE', 'recorded_time_us', format='utc_iso')])
        self.assertEqual(result['submission']['answers'][2]['status'], 'unknown')
        self.assertIn('not_action', result['unsupported'][0]['meaning_checks'][0]['offered']['semantic_type'])

    def test_anyof_requires_all_declared_roles_and_parent_annotation_cannot_be_bypassed(self):
        contract = public()
        contract['questions'][0]['answer_schema'] = {'anyOf': [
            {'type': 'string', requirements.KEY: need('program')},
            {'type': 'string', requirements.KEY: need('email_application_product_with_version')}]}
        self.assertEqual(self.project(contract)['submission']['answers'][0]['status'], 'unknown')
        contract['questions'][0]['answer_schema'] = {'type': 'object', requirements.KEY: need('program'),
                                                    'properties': {'child': {'type': 'string'}}}
        result = self.project(contract, [binding(self.certs[0], 'MAIL', 'program', ['child'])])
        self.assertEqual(result['unsupported'][0]['reason'], 'claim_requirement_must_annotate_exact_answer_value')

    def test_bad_requirements_fail_closed(self):
        for bad in ({}, None, need(''), dict(need('program'), selectors=[]),
                    dict(need('program'), expected='private value'),
                    dict(need('program'), semantic_types=['program', 'program'])):
            with self.subTest(requirement=bad):
                contract = public()
                contract['questions'][0]['answer_schema'][requirements.KEY] = bad
                result = self.project(contract)
                self.assertEqual(result['submission']['answers'][0]['status'], 'unknown')
                self.assertTrue(result['unsupported'][0]['reason'].startswith('invalid_public_claim_requirement'))

    def test_a_keeps_wrong_proposal_values_and_b_only_filters_frozen_candidates(self):
        candidate = {'finding_id': 'WRONG', 'claim': {'exactly': ['usbInsert', 99]}}
        contract = {'schema_version': 2, 'case_id': 'another-case', 'questions': [
            {'id': 'COUNT', 'prompt': 'Extracted count?', 'answer_schema': {'type': 'integer',
             requirements.KEY: need('asserted_extracted_record_count')}}]}
        result = self.project(contract, [binding(candidate, 'COUNT', 'count')], [candidate])
        self.assertEqual(result['submission']['answers'][0]['answer'], 99)
        self.assertEqual(render_projection(result['projection'], admitted_ids=[])['submission']['answers'][0]['status'], 'unknown')
        self.assertEqual(render_projection(result['projection'])['submission']['answers'][0]['answer'], 99)

    def test_preflight_lists_evidence_needs_without_claiming_availability(self):
        schema = public()['questions'][0]['answer_schema']
        view = requirements.inspect(schema, catalog()['forms'])
        self.assertEqual(view['requirements'][0]['status'], 'no_catalog_support')
        self.assertEqual(view['requirements'][0]['available_fields'], [])
        schema[requirements.KEY] = need('program', [{'form': 'programInstalledAt', 'field': 'program'}])
        view = requirements.inspect(schema, catalog()['forms'])
        self.assertEqual(view['requirements'][0]['available_fields'], [
            {'form': 'programInstalledAt', 'field': 'program', 'semantic_type': 'program'}])
        bounded = requirements.inspect({'properties': {str(i): {} for i in range(4097)}}, catalog()['forms'])
        self.assertEqual(bounded['requirements'][0]['reason'], 'requirement_preflight_limit')

    def test_preflight_includes_schema_valued_additional_properties_and_unsupported_references(self):
        contract = public()
        leaf = {'type': 'string', requirements.KEY: need('not_available')}
        schema = {'type': 'object', 'additionalProperties': leaf}
        contract['questions'][0]['answer_schema'] = schema
        view = requirements.inspect(schema, catalog()['forms'])
        self.assertEqual(view['requirements'][0]['path'], [{'additional_property': True}])
        self.assertEqual(view['requirements'][0]['status'], 'no_catalog_support')
        result = self.project(contract, [binding(self.certs[0], 'MAIL', 'program', ['arbitrary_key'])])
        self.assertEqual(result['unsupported'][0]['reason'], 'claim_role_does_not_meet_public_requirement')
        view = requirements.inspect({'$ref': '#/hidden'}, catalog()['forms'])
        self.assertEqual(view['requirements'][0]['reason'], 'unsupported_schema_reference_or_union')

    def test_product_tool_and_report_recompute_the_same_requirement(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for path in Path(self.saved.name).iterdir():
                (root / path.name).write_bytes(path.read_bytes())
            contract = public()
            Investigation(root).initialize(contract)
            (root / 'questions.json').write_text(json.dumps(contract))
            view = answer(root, 'MAIL')
            self.assertEqual(view['field_requirements']['requirements'][0]['status'], 'no_catalog_support')
            result = answer(root, 'MAIL', [{'finding_id': 'F1', 'field': 'program', 'path': []}])
            self.assertEqual(result['submission']['answers'][0]['status'], 'unknown')
            bundle = export.bundle(root, 'Synthetic case')
            # Refused proposals are preview diagnostics, not durable answers.
            retained = project_bundle(bundle, contract)
            self.assertEqual(retained['submission']['answers'][0]['status'], 'unknown')
            self.assertEqual(retained['unsupported'], [])
            self.assertIn('claim_role_does_not_meet_public_requirement',
                          [row['reason'] for row in result['unsupported']])

    def test_separate_debug_profile_retains_observations_and_declares_missing_stronger_roles(self):
        path = Path(__file__).resolve().parent.parent / 'eval/contracts/answer_meaning_debug_v1/questions.json'
        contract = json.loads(path.read_text())
        result = self.project(contract, [binding(self.certs[0], 'Q18', 'program', ['application']),
            binding(self.certs[0], 'Q18', 'program', ['observations', 0, 'executable'])])
        self.assertEqual(result['submission']['answers'][0]['answer'],
                         {'observations': [{'executable': 'POSTBOX.EXE'}]})
        for question in contract['questions']:
            view = requirements.inspect(question['answer_schema'], catalog()['forms'])
            for row in view['requirements']:
                expected = 'catalog_support' if row['path'][0] == 'observations' else 'no_catalog_support'
                self.assertEqual(row['status'], expected, row)


if __name__ == '__main__':
    unittest.main()
