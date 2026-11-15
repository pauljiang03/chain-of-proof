"""Persistent work notes are public, bounded and never carry proof across runs."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent.case import CaseProfile
from agent.investigation import Investigation, atomic_json, current_certificates, question_spec


def profile():
    return CaseProfile('Arbitrary case', 'Public brief', ('Which files?', 'What remains unknown?'),
                       'America/Los_Angeles', 'other-case')


def public():
    return {'schema_version': 2, 'case_id': 'other-case', 'title': 'Arbitrary case',
            'time_zone': 'America/Los_Angeles', 'questions': [
                {'id': 'FILES', 'prompt': 'Which files?', 'answer_schema': {'type': 'array'}},
                {'id': 'GAPS', 'prompt': 'What remains unknown?', 'answer_schema': {'type': 'object'}}]}


def certificate(directory, fid='F1', status='verified', question='Q1'):
    # Recorded synthetic status is enough for linkage tests; no claim of a real proof.
    row = {'finding_id': fid, 'status': status, 'question': question, 'claim': {'fileRecorded': [7]},
           'english': 'The synthetic record names <a> & b.\nIt does not prove a copy.',
           'cited_facts': [{'id': 7}], 'rules': ['R1'], 'strength': 'strong', 'trust_tier': 'kernel',
           'axioms': [], 'lean_file': fid + '.lean'}
    (directory / (fid + '.json')).write_text(json.dumps(row))
    (directory / (fid + '.lean')).write_text('-- synthetic fixture, not a proof\n')
    with (directory / 'proposals.jsonl').open('a') as stream:
        stream.write(json.dumps(row) + '\n')
    return row


class InvestigationState(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.plan = Investigation(self.directory)

    def test_initialization_preserves_all_public_questions_and_unknown_work(self):
        self.assertEqual(self.plan.snapshot()['status'], 'unavailable')
        state = self.plan.initialize(profile())
        self.assertEqual([q['id'] for q in state['questions']], ['Q1', 'Q2'])
        self.assertTrue(all(q['work_status'] == 'not_started' and q['finding_ids'] == [] for q in state['questions']))
        self.assertEqual(state['time_zone'], 'America/Los_Angeles')
        self.assertNotIn('NIST', json.dumps(state))
        self.assertEqual(self.plan.initialize(profile()), state)
        state['questions'][0]['prompt'] = 'local mutation'
        self.assertEqual(self.plan.snapshot()['questions'][0]['prompt'], 'Which files?')
        with self.assertRaises(ValueError):
            self.plan.initialize(CaseProfile('Changed', 'Brief', ('different',)))

    def test_public_schema_ids_and_private_field_rejection(self):
        state = self.plan.initialize(profile(), public())
        self.assertEqual([q['id'] for q in state['questions']], ['FILES', 'GAPS'])
        self.assertEqual(state['questions'][0]['answer_schema'], {'type': 'array'})
        for mutate in (
            lambda p: p.update(expected={'secret': 1}),
            lambda p: p['questions'][0].update(answer='secret'),
            lambda p: p.update(case_id='different-case'),
            lambda p: p['questions'][1].update(id='FILES'),
            lambda p: p.update(time_zone='No/Such_Zone'),
        ):
            data = public()
            mutate(data)
            with self.assertRaises(ValueError):
                question_spec(profile(), data)

    def test_updates_bind_current_verified_ids_keep_history_and_work_is_not_completeness(self):
        self.plan.initialize(profile())
        certificate(self.directory)
        first = self.plan.update('Q1', finding_ids=['F1'], searched=['files by extension'],
                                 unresolved=['original location'], next_actions=['inspect journal'], status='in_progress')
        second = self.plan.update('Q1', finding_ids=['F1'], searched=['files by extension', 'journal names'],
                                  unresolved=[], next_actions=[], status='reviewed')
        question = second['questions'][0]
        self.assertEqual(question['finding_ids'], ['F1'])
        self.assertEqual(question['searched'], ['files by extension', 'journal names'])
        self.assertEqual(question['unresolved'], [])
        self.assertEqual(second['history'][:2], first['history'])
        self.assertEqual([e['sequence'] for e in second['history']], [1, 2, 3])
        self.assertIn('Reviewed does not mean answered', second['disclaimer'])
        self.assertEqual(second['questions'][1]['work_status'], 'not_started')

    def test_wrong_run_rejected_conflicting_and_tampered_certificates_are_refused(self):
        self.plan.initialize(profile())
        original = self.plan.path.read_bytes()
        with self.assertRaises(ValueError):
            self.plan.update('Q1', finding_ids=['Foreign'])
        certificate(self.directory, 'R1', 'rejected')
        with self.assertRaises(ValueError):
            self.plan.update('Q1', finding_ids=['R1'])
        row = certificate(self.directory)
        row['english'] = 'Tampered arbitrary answer'
        (self.directory / 'F1.json').write_text(json.dumps(row))
        with self.assertRaises(ValueError):
            self.plan.update('Q1', finding_ids=['F1'])
        self.assertEqual(self.plan.path.read_bytes(), original)
        with self.assertRaises(ValueError):
            self.plan.update('Q1', finding_ids=['../../F1'])

    def test_symlinks_and_bounded_arguments_do_not_modify_saved_state(self):
        self.plan.initialize(profile())
        original = self.plan.path.read_bytes()
        for arguments in ({'searched': 'not a list'}, {'searched': ['x' * 1001]},
                          {'next_actions': ['x'] * 513}, {'status': 'proven_complete'}):
            with self.assertRaises(ValueError):
                self.plan.update('Q1', **arguments)
        with self.assertRaises(ValueError):
            self.plan.update('Q999', status='reviewed')
        self.assertEqual(self.plan.path.read_bytes(), original)
        certificate(self.directory)
        target = self.directory / 'original.json'
        (self.directory / 'F1.json').rename(target)
        (self.directory / 'F1.json').symlink_to(target)
        with self.assertRaises(ValueError):
            current_certificates(self.directory, ['F1'])
        self.plan.path.unlink()
        self.plan.path.symlink_to(target)
        with self.assertRaises(ValueError):
            self.plan.snapshot()

    def test_concurrent_instances_preserve_every_update_and_monotonic_history(self):
        self.plan.initialize(profile())
        def update(index):
            return Investigation(self.directory).update('Q1', searched=[f'search {index}'])
        with ThreadPoolExecutor(max_workers=6) as pool:
            list(pool.map(update, range(20)))
        state = self.plan.snapshot()
        self.assertEqual(state['revision'], 21)
        self.assertEqual(len(state['questions'][0]['searched']), 20)
        self.assertEqual([e['sequence'] for e in state['history']], list(range(1, 22)))

    def test_atomic_write_failure_keeps_prior_json_and_removes_temporary_files(self):
        self.plan.initialize(profile())
        before = self.plan.path.read_bytes()
        with patch('agent.investigation.os.replace', side_effect=OSError('synthetic write failure')):
            with self.assertRaises(OSError):
                self.plan.update('Q1', searched=['new search'])
        self.assertEqual(self.plan.path.read_bytes(), before)
        self.assertEqual(list(self.directory.glob('.investigation.json.*')), [])
        with self.assertRaises(ValueError):
            atomic_json(self.plan.path, {'invalid': float('nan')})
        self.assertEqual(self.plan.path.read_bytes(), before)

    def test_changed_evidence_requires_new_run_continuation_clears_proof_and_status(self):
        atomic_json(self.directory / 'run-manifest.json', {'inputs': {'facts': {'sha256': 'a' * 64}}})
        self.plan.initialize(profile())
        certificate(self.directory)
        self.plan.update('Q1', finding_ids=['F1'], searched=['found names'], unresolved=['path'], status='reviewed')
        context = self.plan.continuation()
        self.assertNotIn('F1', json.dumps(context))
        new_dir = self.directory / 'new'
        new_dir.mkdir()
        atomic_json(new_dir / 'run-manifest.json', {'inputs': {'facts': {'sha256': 'b' * 64}}})
        context['questions'][0].update(finding_ids=['F1'], work_status='reviewed')
        new = Investigation(new_dir).initialize(profile(), continuation=context)
        self.assertEqual(new['questions'][0]['finding_ids'], [])
        self.assertEqual(new['questions'][0]['work_status'], 'not_started')
        self.assertEqual(new['questions'][0]['searched'], [])
        self.assertEqual(new['questions'][0]['previous_run_notes']['searched'], ['found names'])
        self.assertEqual(new['questions'][0]['previous_run_notes']['status'], 'unverified')
        atomic_json(self.directory / 'run-manifest.json', {'inputs': {'facts': {'sha256': 'c' * 64}}})
        with self.assertRaises(ValueError):
            self.plan.snapshot()

    def test_corrupt_history_is_refused_without_repairing_it(self):
        state = self.plan.initialize(profile())
        state['history'][0]['sequence'] = 2
        atomic_json(self.plan.path, state)
        before = self.plan.path.read_bytes()
        with self.assertRaises(ValueError):
            self.plan.update('Q1', status='reviewed')
        self.assertEqual(self.plan.path.read_bytes(), before)

    def test_repeated_continuation_retains_notes_and_respects_explicit_resolutions(self):
        self.plan.initialize(profile())
        self.plan.update('Q1', searched=['first search'], unresolved=['old gap'], next_actions=['inspect next'])
        next_plan = Investigation(self.directory / 'next')
        next_plan.initialize(profile(), continuation=self.plan.continuation())
        next_plan.update('Q1', searched=['second search'], unresolved=[])
        context = next_plan.continuation()
        self.assertEqual(context['questions'][0]['searched'], ['first search', 'second search'])
        self.assertEqual(context['questions'][0]['unresolved'], [])
        self.assertEqual(context['questions'][0]['next_actions'], ['inspect next'])
        self.assertNotIn('finding_ids', json.dumps(context))

    def test_continuation_allows_new_followup_questions_without_transplanting_old_notes(self):
        self.plan.initialize(profile(), public())
        self.plan.update('FILES', searched=['prior search'], status='reviewed')
        context = self.plan.continuation()
        extended = public()
        extended['questions'].insert(0, {'id': 'FOLLOWUP1', 'prompt': 'Inspect another artifact', 'answer_schema': {}})
        next_plan = Investigation(self.directory / 'extended')
        state = next_plan.initialize(extended, continuation=context)
        new, prior, untouched = state['questions']
        self.assertEqual(new['work_status'], 'not_started')
        self.assertEqual(new['finding_ids'], [])
        self.assertNotIn('previous_run_notes', new)
        self.assertEqual(prior['previous_run_notes']['searched'], ['prior search'])
        self.assertEqual(untouched['id'], 'GAPS')
        reworded = deepcopy(extended)
        reworded['questions'][1]['prompt'] = 'Different question under the same ID'
        with self.assertRaises(ValueError):
            Investigation(self.directory / 'reworded').initialize(reworded, continuation=context)
        dropped = deepcopy(extended)
        dropped['questions'] = dropped['questions'][:2]
        with self.assertRaises(ValueError):
            Investigation(self.directory / 'dropped').initialize(dropped, continuation=context)


if __name__ == '__main__':
    unittest.main()
