"""Bounded recorded-work diagnostics; never infer answers from returned records."""
from collections import Counter
from agent.coverage_plan import coverage_pass

MAX_SAMPLE = 20
MAX_QUESTIONS = 100
LIMITATION = ('Counts describe authored bindings, literal projection and returned inventory pages only. '
              'Inventory counts sum page returns and may repeat records across traversals. Unused candidates and returned-but-unbound rows are prompts for review, not evidence of '
              'relevance, inspection, accuracy, missing answers or semantic completeness. No answers are repaired.')


def completion_diagnostics(public, document, projection, candidates, inventory=None, *, checkpoint=None):
    """Summarize existing literal outputs without exposing answer values."""
    plan = dict(public, facts_sha256=(projection.get('projection', {}).get('evidence_facts_sha256')))
    coverage = coverage_pass(plan, answers=projection['submission'], inventory_progress=inventory)
    authored = Counter(row.get('question_id') for row in document['bindings'] if isinstance(row, dict))
    surviving = Counter(row['question_id'] for row in projection.get('leaves', []))
    referenced = {row.get('candidate_id') for row in document['bindings'] if isinstance(row, dict)}
    ids = [row.get('candidate_id', row.get('finding_id')) for row in candidates]
    unused = [cid for cid in ids if cid not in referenced]
    returned = Counter()
    if inventory is not None and coverage['inputs']['inventory']['status'] == 'recorded':
        for traversal in inventory['traversals']:
            count = traversal.get('rows_returned')
            if type(count) is int and count >= 0:
                returned[traversal['question_id']] += count
    questions = []
    for row in coverage['questions']:
        qid = row['question_id']
        questions.append({'question_id': qid, 'authored_bindings': authored[qid],
            'surviving_leaves': surviving[qid], 'answer_status': row['answer_status'],
            'missing_required_fields': row['missing_required_fields'][:8],
            'missing_required_fields_truncated': len(row['missing_required_fields']) > 8,
            'diagnostics': [kind for kind in row['diagnostics'] if kind not in ('no_recorded_searches', 'not_started')],
            'pending_inventory': len(row['pending_inventory']),
            'inventory_rows_returned': returned[qid],
            'returned_rows_with_zero_authored_bindings': returned[qid] if not authored[qid] else 0,
            'returned_rows_with_zero_surviving_leaves': returned[qid] if not surviving[qid] else 0})
    return {'status': 'uncertified', 'checkpoint': checkpoint,
            'counts': {'questions': len(questions), 'authored_bindings': len(document['bindings']),
                'surviving_leaves': sum(surviving.values()),
                'unknown_questions': sum(row['answer_status'] == 'unknown' for row in questions),
                'missing_required_fields': coverage['counts']['missing_required_fields'],
                'unsupported_bindings': len(projection.get('unsupported', [])),
                'conflicts': len(projection.get('conflicts', [])),
                'unused_candidates': len(unused), 'current_candidates': len(ids),
                'returned_rows_with_zero_authored_bindings': sum(row['returned_rows_with_zero_authored_bindings'] for row in questions)},
            'unused_candidate_ids': unused[:MAX_SAMPLE], 'unused_candidates_truncated': len(unused) > MAX_SAMPLE,
            'inventory_status': coverage['inputs']['inventory']['status'],
            'questions': questions[:MAX_QUESTIONS], 'questions_truncated': len(questions) > MAX_QUESTIONS, 'limitation': LIMITATION}
