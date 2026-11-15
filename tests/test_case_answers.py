"""Generic product answers copy certificates without claiming question accuracy."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from agent.answers import build_answers, enrich_bundle
from agent.investigation import Investigation
from checker.export import bundle
from tests.test_investigation import certificate, profile, public


class CaseAnswers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.plan = Investigation(self.directory)

    def test_exact_certified_sentences_and_all_unanswered_questions_are_preserved(self):
        state = self.plan.initialize(profile())
        cert = certificate(self.directory)
        state = self.plan.update('Q1', finding_ids=['F1'], unresolved=['which original path?'], status='reviewed')
        run = {'case': {'case_id': 'other-case'}, 'findings': [cert], 'rejections': []}
        original = deepcopy(run)
        answers = build_answers(run, state)
        self.assertEqual(run, original)
        self.assertEqual(len(answers['questions']), 2)
        first, second = answers['questions']
        self.assertEqual(first['certified_findings'][0]['sentence'], cert['english'])
        self.assertEqual(first['certified_findings'][0]['finding_id'], 'F1')
        self.assertEqual(first['status'], 'findings_available')
        self.assertEqual(first['completeness'], 'not_established')
        self.assertEqual(first['accuracy'], 'not_evaluated')
        self.assertEqual(second['status'], 'unanswered')
        self.assertEqual(second['certified_findings'], [])
        self.assertEqual(first['unresolved'], ['which original path?'])

    def test_reviewed_work_and_arbitrary_notes_never_become_certified_answers(self):
        self.plan.initialize(profile())
        state = self.plan.update('Q1', searched=['I think the file was copied'], unresolved=['Needs a record'], status='reviewed')
        answers = build_answers({'case': {}, 'findings': [], 'rejections': []}, state)
        row = answers['questions'][0]
        self.assertEqual(row['status'], 'unanswered')
        self.assertEqual(row['work_status'], 'reviewed')
        self.assertEqual(row['certified_findings'], [])
        self.assertNotIn('answer', row)

    def test_exact_question_labels_only_no_fuzzy_or_cross_question_assignment(self):
        state = self.plan.initialize(public())
        cert = certificate(self.directory, question='FILES')
        similar = dict(cert, finding_id='F2', question='FILES maybe')
        answers = build_answers({'case': {}, 'findings': [cert, similar], 'rejections': []}, state)
        self.assertEqual([f['finding_id'] for f in answers['questions'][0]['certified_findings']], ['F1'])
        self.assertEqual(answers['questions'][1]['certified_findings'], [])

    def test_ambiguous_shared_prompts_do_not_assign_one_finding_to_two_questions(self):
        data = public()
        data['questions'][1]['prompt'] = data['questions'][0]['prompt']
        state = self.plan.initialize(data)
        cert = certificate(self.directory, question='Which files?')
        answers = build_answers({'case': {}, 'findings': [cert]}, state)
        self.assertTrue(all(q['status'] == 'unanswered' for q in answers['questions']))

    def test_refusals_missing_and_invalid_links_are_separate_from_certificate_sentences(self):
        state = self.plan.initialize(profile())
        state['questions'][0]['finding_ids'] = ['missing', 'R1', 'DUP']
        rejected = certificate(self.directory, 'R1', 'rejected')
        rejected.update(reason='wrong kind', proof_gap={'status': 'diagnostic', 'summary': 'Need a different record'})
        duplicate = certificate(self.directory, 'DUP')
        run = {'case': {}, 'findings': [rejected, duplicate, deepcopy(duplicate)], 'rejections': [rejected]}
        row = build_answers(run, state)['questions'][0]
        self.assertEqual(row['status'], 'unanswered')
        self.assertEqual(row['certified_findings'], [])
        self.assertEqual(len(row['issues']), 3)
        self.assertEqual(row['refusals'][0]['proof_gap'], rejected['proof_gap'])
        self.assertEqual(row['refusals'][0]['reason'], 'wrong kind')

    def test_export_enriches_existing_bundle_and_never_overwrites_evaluation_answers(self):
        self.plan.initialize(profile())
        cert = certificate(self.directory)
        self.plan.update('Q1', finding_ids=['F1'])
        evaluation = self.directory / 'answers.json'
        evaluation.write_text('{"sentinel":"private evaluation output"}\n')
        before = evaluation.read_bytes()
        exported = bundle(self.directory, 'Public case', case_metadata={'case_id': 'other-case'})
        self.assertEqual(exported['investigation']['revision'], 2)
        answers = json.loads((self.directory / 'case-answers.json').read_text())
        self.assertEqual(exported['case_answers'], answers)
        self.assertEqual(answers['questions'][0]['certified_findings'][0]['sentence'], cert['english'])
        self.assertEqual(evaluation.read_bytes(), before)

    def test_legacy_without_public_questions_is_explicitly_unavailable(self):
        certificate(self.directory)
        exported = bundle(self.directory, 'Legacy')
        self.assertEqual(exported['case_answers']['status'], 'unavailable')
        self.assertEqual(exported['investigation']['status'], 'unavailable')
        self.assertFalse((self.directory / 'case-answers.json').exists())

    def test_export_initializes_from_public_questions_only_and_keeps_unknowns(self):
        result = enrich_bundle({'case': {}, 'findings': [], 'rejections': []}, self.directory, public())
        self.assertEqual([q['id'] for q in result['case_answers']['questions']], ['FILES', 'GAPS'])
        self.assertTrue(all(q['status'] == 'unanswered' for q in result['case_answers']['questions']))
        self.assertTrue((self.directory / 'investigation.json').is_file())

    def test_cross_case_evidence_conflicts_and_sidecar_symlinks_fail_closed(self):
        state = self.plan.initialize(profile())
        with self.assertRaises(ValueError):
            build_answers({'case': {'case_id': 'different'}, 'findings': []}, state)
        state['facts_sha256'] = 'a' * 64
        with self.assertRaises(ValueError):
            build_answers({'case': {'facts_sha256': 'b' * 64}, 'findings': []}, state)
        outside = self.directory / 'target.json'
        outside.write_text('keep me')
        (self.directory / 'case-answers.json').symlink_to(outside)
        with self.assertRaises(ValueError):
            enrich_bundle({'case': {}, 'findings': []}, self.directory)
        self.assertEqual(outside.read_text(), 'keep me')

    def test_conflicting_public_profile_marks_answers_invalid_without_losing_certificates(self):
        cert = certificate(self.directory)
        exported = bundle(self.directory, 'Other', case_metadata={'case_id': 'different-case'}, public_questions=public())
        self.assertEqual(exported['findings'][0]['english'], cert['english'])
        self.assertEqual(exported['case_answers']['status'], 'invalid')
        self.assertFalse(self.plan.path.exists())

    def test_conflict_and_continuation_sidecars_stay_separate_diagnostics(self):
        certificate(self.directory)
        review = {'schema_version': 1, 'status': 'diagnostic', 'scope': {'records_examined': 1},
                  'diagnostics': [{'id': 'D1', 'status': 'diagnostic', 'summary': 'Needs review'}]}
        receipt = {'schema_version': 1, 'same_evidence': False, 'replay_log': 'continuation-replay.json', 'parent': '/previous/run'}
        replay = {'schema_version': 1, 'replayed': []}
        (self.directory / 'review.json').write_text(json.dumps(review))
        (self.directory / 'continuation.json').write_text(json.dumps(receipt))
        (self.directory / 'continuation-replay.json').write_text(json.dumps(replay))
        exported = bundle(self.directory, 'Diagnostic')
        self.assertEqual(exported['conflicts'], review)
        self.assertEqual(exported['continuation'], receipt)
        self.assertEqual(exported['continuation_replay'], replay)
        self.assertEqual(len(exported['findings']), 1)
        review['status'] = 'verified'
        (self.directory / 'review.json').write_text(json.dumps(review))
        with self.assertRaises(ValueError):
            bundle(self.directory, 'Invalid review')


if __name__ == '__main__':
    unittest.main()
