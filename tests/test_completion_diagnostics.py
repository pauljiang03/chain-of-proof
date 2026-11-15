"""Bounded counts retain operational gaps without exposing answer values."""
import json
import unittest
from agent.completion_diagnostics import completion_diagnostics
from agent.coverage_plan import coverage_pass


class CompletionDiagnostics(unittest.TestCase):
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
