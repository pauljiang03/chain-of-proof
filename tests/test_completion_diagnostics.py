"""Bounded counts retain operational gaps without exposing answer values."""
import json
import unittest
from unittest.mock import patch
import agent.completion_diagnostics as diagnostics
from agent.answer_projection import catalog
from agent.answer_requirements import inspect
from tests.test_answer_requirements import need
from agent.completion_diagnostics import completion_diagnostics
from agent.coverage_plan import coverage_pass


class CompletionDiagnostics(unittest.TestCase):
    def test_one_array_row_without_traversal_warns_without_inventing_missing_rows(self):
        public = {'case_id': 'C', 'questions': [{'id': 'Q', 'answer_schema': {
            'type': 'object', 'properties': {'records': {'type': 'array', 'items': {'type': 'string'}}}}}]}
        projection = {'submission': {'schema_version': 2, 'case_id': 'C', 'answers': [{
            'question_id': 'Q', 'status': 'answered', 'answer': {'records': ['observed']}}]},
            'leaves': [{'question_id': 'Q'}], 'unsupported': [], 'conflicts': []}
        result = completion_diagnostics(public, {'bindings': [{'question_id': 'Q', 'candidate_id': 'A'}]}, projection, [])
        row = result['questions'][0]
        self.assertEqual(row['answer_status'], 'answered')
        self.assertEqual(row['missing_required_fields'], [])
        self.assertIn('array_inventory_coverage_unknown', row['diagnostics'])
        self.assertEqual(row['inventory_population_coverage'], 'unknown')
        self.assertEqual(result['question_completeness'], 'not_established')

    def test_returned_rows_are_not_answers_and_no_values_are_returned(self):
        public = {'case_id': 'C', 'questions': [{'id': 'Q', 'answer_schema': {'type': 'string'}}]}
        projection = {'submission': {'schema_version': 2, 'case_id': 'C', 'answers': [{'question_id': 'Q', 'status': 'unknown'}]},
            'projection': {'evidence_facts_sha256': 'a'*64}, 'leaves': [], 'unsupported': [], 'conflicts': []}
        inventory = {'status': 'recorded', 'evidence_sha256': 'a'*64, 'traversals': [{
            'question_id': 'Q', 'exhausted': True, 'page_size': 250, 'rows_returned': 1500}]}
        result = completion_diagnostics(public, {'bindings': [], 'unanswered': []}, projection,
            [{'candidate_id': 'P'+str(i), 'claim': {'secret': 'VALUE_NOT_FOR_DISPLAY'}} for i in range(200)], inventory)
        self.assertEqual(result['counts']['returned_rows_with_zero_authored_bindings'], 1500)
        self.assertEqual(result['counts']['unknown_questions'], 1)
        self.assertEqual(result['counts']['unused_candidates'], 200)
        self.assertEqual(len(result['unused_candidate_ids']), 20)
        self.assertTrue(result['unused_candidates_truncated'])
        self.assertNotIn('VALUE_NOT_FOR_DISPLAY', json.dumps(result))

    def test_partial_answer_reports_missing_required_fields_without_value_dump(self):
        public = {'case_id': 'C', 'questions': [{'id': 'Q', 'answer_schema': {
            'type': 'object', 'required': ['known', 'missing'], 'properties': {
                'known': {'type': 'string'}, 'missing': {'type': 'string'}}}}]}
        projection = {'submission': {'schema_version': 2, 'case_id': 'C', 'answers': [{
            'question_id': 'Q', 'status': 'answered', 'answer': {'known': 'PRIVATE_LITERAL'}}]},
            'leaves': [{'question_id': 'Q'}], 'unsupported': [], 'conflicts': []}
        result = completion_diagnostics(public, {'bindings': [{'question_id': 'Q', 'candidate_id': 'C1'}]},
                                        projection, [{'candidate_id': 'C1'}])
        self.assertEqual(result['counts']['surviving_leaves'], 1)
        self.assertEqual(result['counts']['missing_required_fields'], 1)
        self.assertEqual(result['questions'][0]['missing_required_fields'], ['/missing'])
        self.assertNotIn('PRIVATE_LITERAL', json.dumps(result))

    def declaration_fixture(self):
        def schema(role, unavailable=False):
            return {'type': 'string', 'x-claim-requirement': need(role), 'x-claim-scope':
                {'mode': 'unavailable', 'meaning': 'Reviewed missing source fixture.'} if unavailable else
                {'mode': 'unscoped_observation', 'meaning': 'Synthetic observation fixture.'}}
        public = {'case_id': 'C', 'questions': [
            {'id': 'SUPPORTED', 'answer_schema': schema('device_serial')},
            {'id': 'UNSUPPORTED', 'answer_schema': schema('reviewed_role_without_catalog_support')},
            {'id': 'UNAVAILABLE', 'answer_schema': schema('device_serial', True)},
            {'id': 'UNBOUND', 'answer_schema': schema('device_serial')}]}
        projection = {'submission': {'schema_version': 2, 'case_id': 'C', 'answers': [
            {'question_id': q['id'], 'status': 'unknown'} for q in public['questions']]},
            'projection': {'evidence_facts_sha256': 'a'*64}, 'leaves': [],
            'unsupported': [{'binding_index': 0, 'binding': {'question_id': 'SUPPORTED'}}],
            'conflicts': [{'question_id': 'SUPPORTED', 'binding_indices': [0, 1]},
                          {'question_id': 'SUPPORTED', 'binding_indices': [0]}]}
        document = {'bindings': [{'question_id': 'SUPPORTED', 'candidate_id': 'A'},
                                 {'question_id': 'SUPPORTED', 'candidate_id': 'B'}]}
        return public, document, projection

    def test_catalog_scope_refusals_and_unbound_are_separate_from_source_presence(self):
        public, document, projection = self.declaration_fixture()
        inventory = {'status': 'recorded', 'evidence_sha256': 'a'*64, 'traversals': [{
            'question_id': 'SUPPORTED', 'exhausted': True, 'page_size': 100, 'rows_returned': 0}]}
        result = completion_diagnostics(public, document, projection, [], inventory)
        rows = {row['question_id']: row for row in result['questions']}
        self.assertEqual(rows['SUPPORTED']['public_declarations']['catalog_supported_fields'], 1)
        self.assertEqual(rows['SUPPORTED']['authored_refused_bindings'], 1)
        self.assertEqual(rows['SUPPORTED']['binding_conflicts'], 2)
        self.assertEqual(rows['SUPPORTED']['conflicting_authored_bindings'], 2)
        self.assertEqual(rows['SUPPORTED']['inventory_recording'], 'recorded_inventory')
        self.assertEqual(rows['SUPPORTED']['inventory_rows_returned'], 0)
        self.assertEqual(rows['UNBOUND']['inventory_recording'], 'no_recorded_inventory')
        self.assertEqual(rows['UNBOUND']['authored_binding_status'], 'no_authored_bindings')
        self.assertEqual(rows['UNBOUND']['public_declarations']['catalog_supported_fields'], 1)
        self.assertEqual(rows['UNSUPPORTED']['public_declarations']['no_catalog_support_fields'], 1)
        self.assertEqual(rows['UNAVAILABLE']['public_declarations']['unavailable_source_scopes'], 1)
        self.assertTrue(all(row['source_presence'] == 'source_presence_not_determined' for row in rows.values()))
        self.assertTrue(all(row['answer_status'] == 'unknown' for row in rows.values()))
        self.assertEqual(result['question_completeness'], 'not_established')
        self.assertEqual(result['declaration_counts'], {'catalog_supported_fields': 3,
            'no_catalog_support_fields': 1, 'unavailable_source_scopes': 1})
        self.assertNotIn('available_fields', json.dumps(result))
        self.assertNotIn('Reviewed missing source fixture.', json.dumps(result))

    def test_invalid_unavailable_and_unsupplied_inventory_do_not_become_valid_no_traversals(self):
        public, document, projection = self.declaration_fixture()
        cases = [(None, 'inventory_progress_not_supplied'),
            ({'status': 'unavailable', 'traversals': []}, 'inventory_progress_unavailable'),
            ({'status': 'recorded', 'evidence_sha256': 'wrong', 'traversals': []}, 'inventory_progress_invalid'),
            ({'status': 'recorded', 'evidence_sha256': 'a'*64, 'traversals': []}, 'no_recorded_inventory')]
        for inventory, expected in cases:
            with self.subTest(expected=expected):
                result = completion_diagnostics(public, document, projection, [], inventory)
                self.assertTrue(all(row['inventory_recording'] == expected for row in result['questions']))
                self.assertTrue(all(row['source_presence'] == 'source_presence_not_determined' for row in result['questions']))

    def test_catalog_once_and_same_catalog_object_for_each_question(self):
        public, document, projection = self.declaration_fixture()
        form_ids = []
        def inspected(schema, forms, **kwargs):
            form_ids.append(id(forms))
            return inspect(schema, forms, **kwargs)
        with patch.object(diagnostics, 'catalog', wraps=catalog) as fetched, patch.object(diagnostics, 'inspect', side_effect=inspected):
            completion_diagnostics(public, document, projection, [])
        self.assertEqual(fetched.call_count, 1)
        self.assertEqual(len(form_ids), 4)
        self.assertEqual(len(set(form_ids)), 1)

    def test_declaration_inspection_error_is_unavailable_not_zero_no_support(self):
        public, document, projection = self.declaration_fixture()
        with patch.object(diagnostics, 'inspect', side_effect=ValueError('Synthetic inspector failure')):
            result = completion_diagnostics(public, document, projection, [])
        self.assertEqual(result['declaration_inspection_unavailable_questions'], 4)
        self.assertTrue(all(value is None for value in result['declaration_counts'].values()))
        for row in result['questions']:
            self.assertEqual(row['public_declarations']['status'], 'unavailable')
            self.assertIsNone(row['public_declarations']['no_catalog_support_fields'])
        with patch.object(diagnostics, 'catalog', side_effect=RuntimeError('Synthetic catalog failure')):
            failed_catalog = completion_diagnostics(public, document, projection, [])
        self.assertEqual(failed_catalog['declaration_inspection_unavailable_questions'], 4)

    def test_malformed_authored_bindings_remain_diagnostics_not_a_report_failure(self):
        public, document, projection = self.declaration_fixture()
        document['bindings'] += [[], {'question_id': [], 'candidate_id': []}]
        projection['unsupported'] += [{'binding': []}, {'binding': {'question_id': []}}]
        result = completion_diagnostics(public, document, projection, [])
        self.assertEqual(result['counts']['authored_bindings'], 4)
        self.assertEqual(result['counts']['unsupported_bindings'], 3)
        self.assertEqual(result['questions'][0]['authored_refused_bindings'], 1)

    def test_claim_annotations_do_not_create_schema_presence_warnings(self):
        schema = {'type': 'object', 'required': ['other'], 'properties': {'known': {'type': 'string',
            'x-claim-requirement': {}, 'x-claim-scope': {}}}, 'x-claim-row': {'mode': 'independent'}}
        public = {'case_id': 'C', 'questions': [{'id': 'Q', 'answer_schema': schema}]}
        submission = {'schema_version': 2, 'case_id': 'C', 'answers': [{'question_id': 'Q', 'status': 'answered', 'answer': {'known': 'kept'}}]}
        result = coverage_pass(public, submission)
        self.assertEqual(result['questions'][0]['missing_required_fields'], ['/other'])
        self.assertNotIn('schema_review_needed', result['questions'][0]['diagnostics'])


if __name__ == '__main__':
    unittest.main()
