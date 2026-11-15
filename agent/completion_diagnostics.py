"""Bounded recorded-work diagnostics; never infer answers from returned records."""
from collections import Counter
from agent.coverage_plan import coverage_pass
from agent.answer_projection import catalog
from agent.answer_requirements import inspect

MAX_SAMPLE = 20
MAX_QUESTIONS = 100
LIMITATION = ('Counts describe public declarations, authored bindings, literal projection and returned inventory pages only. '
              'Catalog support is not source presence or evidence support. Source presence is not determined by these diagnostics. '
              'Inventory counts sum page returns and may repeat records across traversals. Unused candidates and returned-but-unbound rows are prompts for review, not evidence of '
              'relevance, inspection, accuracy, missing answers or semantic completeness. No answers are repaired.')


def _declarations(schema, forms):
    """Discard available-field catalogs; retain only bounded declaration counts."""
    keys = ('catalog_supported_fields', 'no_catalog_support_fields', 'missing_field_requirements',
            'invalid_requirement_rows', 'declared_source_scopes', 'unavailable_source_scopes')
    try:
        if not isinstance(forms, dict):
            raise ValueError('public field catalog is unavailable')
        if not isinstance(schema, dict):
            raise ValueError('public answer schema is unavailable')
        inspected = inspect(schema, forms, require_claim_requirements=True, require_evidence_scope=True)
        statuses = Counter(row['status'] for row in inspected['requirements'])
        scopes = inspected['scope_requirements']
        return {'status': 'recorded', 'catalog_supported_fields': statuses['catalog_support'],
                'no_catalog_support_fields': statuses['no_catalog_support'],
                'missing_field_requirements': statuses['missing_annotation'],
                'invalid_requirement_rows': statuses['invalid'],
                'declared_source_scopes': len(scopes),
                'unavailable_source_scopes': sum(row['status'] == 'unavailable' for row in scopes)}
    except Exception as error:
        return dict.fromkeys(keys, None) | {'status': 'unavailable', 'error_type': type(error).__name__}


def _question_id(row):
    binding = row.get('binding')
    value = row.get('question_id', binding.get('question_id') if isinstance(binding, dict) else None)
    return value if isinstance(value, str) else None


def completion_diagnostics(public, document, projection, candidates, inventory=None, *, checkpoint=None):
    """Summarize existing literal outputs without exposing answer values."""
    plan = dict(public, facts_sha256=(projection.get('projection', {}).get('evidence_facts_sha256')))
    coverage = coverage_pass(plan, answers=projection['submission'], inventory_progress=inventory)
    authored = Counter(_question_id(row) for row in document['bindings'] if isinstance(row, dict))
    surviving = Counter(row['question_id'] for row in projection.get('leaves', []))
    referenced = {row['candidate_id'] for row in document['bindings']
                  if isinstance(row, dict) and isinstance(row.get('candidate_id'), str)}
    ids = [row.get('candidate_id', row.get('finding_id')) for row in candidates]
    unused = [cid for cid in ids if cid not in referenced]
    refused = Counter(_question_id(row) for row in projection.get('unsupported', []))
    conflicts = Counter(row.get('question_id') for row in projection.get('conflicts', []))
    conflicting_indices = {}
    for conflict in projection.get('conflicts', []):
        conflicting_indices.setdefault(conflict.get('question_id'), set()).update(conflict.get('binding_indices', []))
    # One catalog snapshot per report; never expand or copy it per question.
    try:
        forms = catalog()['forms']
    except Exception:
        forms = None
    declarations = {question['id']: _declarations(question.get('answer_schema'), forms)
                    for question in public['questions']}
    returned, traversals = Counter(), Counter()
    inventory_state = coverage['inputs']['inventory']['status']
    if inventory is not None and inventory_state == 'recorded':
        for traversal in inventory['traversals']:
            traversals[traversal['question_id']] += 1
            count = traversal.get('rows_returned')
            if type(count) is int and count >= 0:
                returned[traversal['question_id']] += count
    questions = []
    for row in coverage['questions']:
        qid = row['question_id']
        inventory_recording = ('recorded_inventory' if traversals[qid] else 'no_recorded_inventory') if inventory_state == 'recorded' else {
            'invalid': 'inventory_progress_invalid', 'unavailable': 'inventory_progress_unavailable',
            'not_supplied': 'inventory_progress_not_supplied'}.get(inventory_state, 'inventory_progress_unavailable')
        questions.append({'question_id': qid, 'authored_bindings': authored[qid],
            'authored_binding_status': 'authored_bindings_present' if authored[qid] else 'no_authored_bindings',
            'authored_refused_bindings': refused[qid], 'binding_conflicts': conflicts[qid],
            'conflicting_authored_bindings': len(conflicting_indices.get(qid, ())),
            'public_declarations': declarations[qid],
            'source_presence': 'source_presence_not_determined',
            'inventory_recording': inventory_recording, 'recorded_inventory_traversals': traversals[qid],
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
            'declaration_counts': {
                key: (sum(row[key] for row in declarations.values()) if all(row['status'] == 'recorded' for row in declarations.values()) else None)
                for key in ('catalog_supported_fields', 'no_catalog_support_fields', 'unavailable_source_scopes')},
            'declaration_inspection_unavailable_questions': sum(row['status'] == 'unavailable' for row in declarations.values()),
            'question_completeness': 'not_established',
            'unused_candidate_ids': unused[:MAX_SAMPLE], 'unused_candidates_truncated': len(unused) > MAX_SAMPLE,
            'inventory_status': coverage['inputs']['inventory']['status'],
            'questions': questions[:MAX_QUESTIONS], 'questions_truncated': len(questions) > MAX_QUESTIONS, 'limitation': LIMITATION}
