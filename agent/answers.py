"""Per-question answer views built from recorded certificate sentences."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from pathlib import Path

from agent.investigation import Investigation, _read_json, atomic_json
from checker.check import valid_finding_id

DISCLAIMER = ('Certified statements are copied verbatim from current-run records marked verified; '
              'this export does not independently replay proofs. Associating a finding with a question '
              'does not prove relevance, answer accuracy or completeness. Work notes and refusal diagnostics '
              'are unverified and separate. This file is not evaluation answers.json.')


def build_answers(run, investigation):
    """Build a view for every public question from certificate sentences only."""
    if not isinstance(run, dict) or not isinstance(investigation, dict):
        raise ValueError('run and investigation must be objects')
    if investigation.get('schema_version') != 1 or not isinstance(investigation.get('questions'), list):
        raise ValueError('answers require a recorded investigation question plan')
    case_id = run.get('case', {}).get('case_id')
    if case_id is not None and investigation.get('case_id') not in (None, case_id):
        raise ValueError('investigation case_id differs from the run')
    facts_hash = run.get('case', {}).get('facts_sha256')
    if facts_hash is not None and investigation.get('facts_sha256') not in (None, facts_hash):
        raise ValueError('investigation belongs to a different evidence snapshot')
    by_id, duplicates = {}, set()
    for finding in run.get('findings', []):
        if not isinstance(finding, dict):
            continue
        fid = finding.get('finding_id')
        if not valid_finding_id(fid):
            continue
        if fid in by_id:
            duplicates.add(fid)
        by_id[fid] = finding
    eligible = {fid: f for fid, f in by_id.items() if fid not in duplicates and f.get('status') == 'verified'
                and isinstance(f.get('english'), str) and f['english']}
    public = investigation['questions']
    if any(not isinstance(q, dict) or not isinstance(q.get('id'), str) or not isinstance(q.get('prompt'), str)
           for q in public):
        raise ValueError('invalid public question in investigation')
    prompt_counts = Counter(q['prompt'] for q in public)
    public_ids = {q['id'] for q in public}
    def matches(label, question):
        if not isinstance(label, str):
            return False
        if label in public_ids:
            return label == question['id']
        return label == question['prompt'] and prompt_counts[label] == 1
    questions = []
    used = set()
    for question in investigation['questions']:
        if not isinstance(question, dict) or not isinstance(question.get('id'), str) or not isinstance(question.get('prompt'), str):
            raise ValueError('invalid public question in investigation')
        if question['id'] in used:
            raise ValueError('duplicate investigation question ID')
        used.add(question['id'])
        ids = question.get('finding_ids', [])
        if not isinstance(ids, list) or any(not isinstance(fid, str) for fid in ids):
            raise ValueError('question finding_ids must be a list of strings')
        # Findings attach automatically only on an exact question label match.
        selected = list(dict.fromkeys(ids + [fid for fid, f in eligible.items() if matches(f.get('question'), question)]))
        issues = [{'finding_id': fid, 'reason': 'No unique current-run verified certificate sentence is available.'}
                  for fid in selected if fid not in eligible]
        sentences = [{'finding_id': fid, 'sentence': eligible[fid]['english'],
                      'strength': eligible[fid].get('strength'),
                      'association': 'agent_plan' if fid in ids else 'exact_question_label'}
                     for fid in selected if fid in eligible]
        refusals = [{'finding_id': rejection.get('finding_id'), 'reason': rejection.get('reason'),
                     'claim': deepcopy(rejection.get('claim')),
                     'proof_gap': deepcopy(rejection.get('proof_gap'))}
                    for rejection in run.get('rejections', []) if isinstance(rejection, dict)
                    and rejection.get('status') == 'rejected' and matches(rejection.get('question'), question)]
        row = {'id': question['id'], 'prompt': question['prompt'],
               'status': 'findings_available' if sentences else 'unanswered',
               'work_status': question.get('work_status', 'not_started'),
               'certified_findings': sentences, 'refusals': refusals,
               'unresolved': deepcopy(question.get('unresolved', [])),
               'next_actions': deepcopy(question.get('next_actions', [])),
               'searched': deepcopy(question.get('searched', [])),
               'issues': issues, 'completeness': 'not_established', 'accuracy': 'not_evaluated'}
        if 'previous_run_notes' in question:
            row['previous_run_notes'] = deepcopy(question['previous_run_notes'])
        questions.append(row)
    return {'schema_version': 1, 'kind': 'certificate_sentence_answers', 'case_id': investigation.get('case_id'),
            'name': investigation.get('name'), 'investigation_revision': investigation.get('revision'),
            'questions': questions, 'completeness': 'not_established', 'accuracy': 'not_evaluated',
            'disclaimer': DISCLAIMER}


def enrich_bundle(run, run_dir, public_questions=None):
    """Attach the plan and answer views to a run and write case-answers.json."""
    directory = Path(run_dir)
    planner = Investigation(directory)
    case_id = run.get('case', {}).get('case_id')
    public_id = public_questions.get('case_id') if isinstance(public_questions, dict) else None
    if case_id is not None and public_id is not None and case_id != public_id:
        diagnostic = {'schema_version': 1, 'status': 'invalid', 'questions': [],
                      'reason': 'Public question case_id conflicts with the selected run; no answer association was made.'}
        run['investigation'] = deepcopy(diagnostic)
        run['case_answers'] = dict(diagnostic, disclaimer=DISCLAIMER)
        atomic_json(directory / 'case-answers.json', run['case_answers'])
        return run
    if planner.path.exists() or planner.path.is_symlink():
        state = planner.snapshot()
    else:
        profile_path = directory / 'case-profile.json'
        if profile_path.exists() or profile_path.is_symlink():
            state = planner.initialize(_read_json(profile_path), public_questions)
        elif public_questions is not None:
            state = planner.initialize(public_questions)
        else:
            run['investigation'] = {'schema_version': 1, 'status': 'unavailable', 'questions': [],
                                    'reason': 'No public question profile or investigation plan was supplied.'}
            run['case_answers'] = {'schema_version': 1, 'status': 'unavailable', 'questions': [],
                                  'reason': 'No public questions were supplied; no answer coverage is inferred.',
                                  'disclaimer': DISCLAIMER}
            return run
    answers = build_answers(run, state)
    atomic_json(directory / 'case-answers.json', answers)
    run['investigation'], run['case_answers'] = state, answers
    return run
