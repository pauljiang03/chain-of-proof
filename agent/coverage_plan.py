"""Bounded public-schema and agent-work diagnostics; never proof or answer scoring."""
from __future__ import annotations

MAX_QUESTIONS = 500
MAX_NODES = 10000
MAX_DEPTH = 16
MAX_PATHS = 64
MAX_ACTIONS = 8
MAX_TRAVERSALS = 128
MAX_POINTER = 512
LIMITATION = ('Diagnostics concern public required fields and recorded work only. Searches are agent-reported; '
              'inventory rows were returned, not necessarily inspected. Neither answer presence, traversal '
              'exhaustion nor these diagnostics establishes semantic completeness, accuracy or certified completeness. '
              'Only directly declared requirements are scanned; other JSON Schema constraints, including types, '
              'values, formats, additional properties and length/count bounds, are not validated.')


def _pointer(path, key):
    return path + '/' + str(key).replace('~', '~0').replace('/', '~1')


def _question_id(value):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 128


def _fields(schema, value, budget):
    missing, notes = [], []
    annotations = {'title', 'description', '$comment', 'examples', 'default', 'readOnly', 'writeOnly', 'deprecated'}
    supported = {'type', 'properties', 'required', 'items'} | annotations
    # These standard constraints do not declare required object-field presence.
    # Their validity remains outside this helper, rather than an actionable gap.
    non_presence = {'$schema', '$id', '$anchor', '$defs', 'definitions', 'enum', 'const', 'format',
                    'additionalProperties', 'unevaluatedProperties', 'patternProperties', 'propertyNames',
                    'minProperties', 'maxProperties', 'minimum', 'maximum', 'exclusiveMinimum',
                    'exclusiveMaximum', 'multipleOf', 'minLength', 'maxLength', 'pattern', 'contentEncoding',
                    'contentMediaType', 'contentSchema', 'minItems', 'maxItems', 'uniqueItems',
                    'additionalItems', 'unevaluatedItems', 'minContains', 'maxContains', 'not'}
    ambiguous = {'anyOf', 'oneOf', 'allOf', 'if', 'then', 'else', '$ref', '$dynamicRef', '$recursiveRef',
                 'dependentRequired', 'dependentSchemas', 'dependencies', 'contains', 'prefixItems'}

    def note(message):
        if message not in notes and len(notes) < MAX_ACTIONS:
            notes.append(message)

    def walk(spec, actual, path, depth):
        if budget[0] <= 0 or depth > MAX_DEPTH or len(missing) >= MAX_PATHS or len(path) > MAX_POINTER:
            note('Bounded scan reached a node, depth, pointer or missing-path limit; review remaining fields manually.')
            return
        budget[0] -= 1
        if not isinstance(spec, dict):
            note('Unsupported public schema shape; required-field coverage is unavailable for this part.')
            return
        if set(spec) & ambiguous:
            note('Alternative, conditional or referenced schema is ambiguous here; only directly declared requirements were scanned.')
        if set(spec) - supported - non_presence - ambiguous:
            note('Unsupported schema keywords may alter required-field presence; review this part manually.')
        required, properties = spec.get('required', []), spec.get('properties', {})
        if (not isinstance(required, list) or len(required) > MAX_NODES
                or any(not isinstance(k, str) for k in required) or not isinstance(properties, dict)):
            note('Invalid public required/properties schema; review this part manually.')
            return
        if isinstance(actual, dict):
            for key in required:
                if budget[0] <= 0 or len(missing) >= MAX_PATHS:
                    note('Bounded scan reached a node or missing-path limit; review remaining fields manually.')
                    break
                budget[0] -= 1
                pointer = _pointer(path, key)
                if len(pointer) > MAX_POINTER:
                    note('Bounded scan reached the pointer limit; review remaining fields manually.')
                elif key not in actual:
                    missing.append(pointer)
            for key, child in properties.items():
                if budget[0] <= 0:
                    note('Bounded scan reached the node limit; review remaining fields manually.')
                    break
                budget[0] -= 1
                if key in actual:
                    walk(child, actual[key], _pointer(path, key), depth + 1)
        elif properties or required:
            # Null may be allowed by the schema. Do not invent missing children.
            if actual is not None:
                note('Object requirements could not be traversed for a non-object value; review the public schema.')
        if isinstance(actual, list) and 'items' in spec:
            for index, item in enumerate(actual):
                if budget[0] <= 0:
                    note('Bounded scan reached the node limit; review remaining array items manually.')
                    break
                walk(spec['items'], item, _pointer(path, index), depth + 1)
    walk(schema, value, '', 0)
    return missing, notes


def coverage_pass(plan, answers=None, inventory_progress=None):
    """Return diagnostics without modifying inputs, repairing answers or reading files."""
    result = {'schema_version': 1, 'status': 'recorded', 'limitation': LIMITATION,
              'inputs': {}, 'questions': [], 'counts': {}}
    questions = plan.get('questions') if isinstance(plan, dict) else None
    if (not isinstance(questions, list) or not 1 <= len(questions) <= MAX_QUESTIONS
            or any(not isinstance(q, dict) or not _question_id(q.get('id')) for q in questions)
            or len({q['id'] for q in questions}) != len(questions)):
        result.update(status='unavailable', reason='A valid bounded public question plan is unavailable.')
        return result
    ids = {q['id'] for q in questions}
    mapped = {}
    answer_state = 'not_supplied'
    if answers is not None:
        answer_state = 'invalid'
        if (isinstance(answers, dict) and answers.get('schema_version') == 2
                and answers.get('case_id') == plan.get('case_id')
                and isinstance(answers.get('answers'), list) and len(answers['answers']) <= MAX_QUESTIONS):
            answer_state = 'supplied'
            for row in answers['answers']:
                if (not isinstance(row, dict) or not _question_id(row.get('question_id'))
                        or row['question_id'] not in ids or row['question_id'] in mapped
                        or row.get('status') not in ('answered', 'unknown', 'unanswered')):
                    answer_state = 'invalid'
                    mapped = {}
                    break
                mapped[row['question_id']] = row
    result['inputs']['answers'] = {'status': answer_state}
    if answer_state == 'invalid':
        result['inputs']['answers']['reason'] = 'Invalid submission shape, duplicate/foreign question IDs or case mismatch; answer diagnostics are unavailable.'
    inventory_state, traversals = 'not_supplied', []
    if inventory_progress is not None:
        inventory_state = 'invalid'
        if isinstance(inventory_progress, dict):
            status = inventory_progress.get('status')
            rows = inventory_progress.get('traversals')
            evidence = inventory_progress.get('evidence_sha256')
            if status == 'unavailable' and rows == []:
                inventory_state = 'unavailable'
            elif (status == 'recorded' and isinstance(rows, list) and len(rows) <= MAX_TRAVERSALS
                  and evidence == plan.get('facts_sha256')):
                inventory_state = 'recorded'
                for row in rows:
                    if (not isinstance(row, dict) or not _question_id(row.get('question_id'))
                            or row['question_id'] not in ids
                            or type(row.get('exhausted')) is not bool
                            or type(row.get('page_size')) is not int or not 1 <= row['page_size'] <= 250
                            or any(row.get(k) is not None and (not isinstance(row[k], list)
                                   or len(row[k]) > 32 or any(not isinstance(v, str) or len(v) > 256 for v in row[k]))
                                   for k in ('kinds', 'exhibits'))
                            or (not row['exhausted'] and (not isinstance(row.get('next_cursor'), str)
                                                        or not 1 <= len(row['next_cursor']) <= 256))):
                        inventory_state, traversals = 'invalid', []
                        break
                    traversals.append(row)
    result['inputs']['inventory'] = {'status': inventory_state}
    if inventory_state == 'invalid':
        result['inputs']['inventory']['reason'] = 'Invalid, stale or unbounded inventory progress; traversal diagnostics are unavailable.'
    counts = {key: 0 for key in ('questions', 'not_started', 'no_recorded_searches', 'unresolved_work',
                                'answer_absent', 'answer_unknown', 'answer_missing', 'missing_required_fields',
                                'schema_review_needed', 'pending_inventory')}
    budget = [MAX_NODES]
    for question in questions:
        qid = question['id']
        row = {'question_id': qid, 'diagnostics': [], 'actions': [], 'missing_required_fields': [],
               'pending_inventory': [], 'answer_status': answer_state if answer_state != 'supplied' else 'absent'}
        def flag(kind, action):
            row['diagnostics'].append(kind)
            counts[kind] += 1
            if len(row['actions']) < MAX_ACTIONS:
                row['actions'].append(action)
        if question.get('work_status') == 'not_started':
            flag('not_started', 'Begin work on this public question or record why work is blocked.')
        if not question.get('searched'):
            flag('no_recorded_searches', 'Record searches performed; absence of a note does not establish absence of evidence work.')
        if question.get('unresolved'):
            flag('unresolved_work', 'Review the saved unresolved work notes for this question.')
        if answer_state == 'supplied':
            answer = mapped.get(qid)
            if answer is None:
                flag('answer_absent', 'Add a draft response or explicitly record uncertainty for this question.')
            elif answer['status'] in ('unknown', 'unanswered'):
                row['answer_status'] = answer['status']
                flag('answer_unknown', 'Review unanswered scope and preserve uncertainty where unsupported.')
            elif 'answer' not in answer:
                row['answer_status'] = 'missing_answer'
                flag('answer_missing', 'An answered draft has no answer value; review the public submission contract.')
            else:
                row['answer_status'] = 'answered'
                schema = question.get('answer_schema')
                if schema is None:
                    flag('schema_review_needed', 'No public answer schema is available for required-field diagnostics.')
                else:
                    missing, notes = _fields(schema, answer['answer'], budget)
                    row['missing_required_fields'] = missing
                    counts['missing_required_fields'] += len(missing)
                    if missing:
                        row['diagnostics'].append('missing_required_fields')
                        row['actions'].append('Review missing required public fields; retain supported partial values and uncertainty.')
                    if notes:
                        flag('schema_review_needed', 'Review schema limitations; this scan does not establish schema validity.')
                        row['schema_notes'] = notes
        for traversal in traversals:
            if traversal['question_id'] == qid and not traversal['exhausted']:
                row['pending_inventory'].append({key: traversal.get(key) for key in
                                                 ('kinds', 'exhibits', 'page_size', 'next_cursor')})
                counts['pending_inventory'] += 1
        if row['pending_inventory']:
            row['actions'].append('Continue inventory_page with this question_id and saved filters, page_size and next_cursor; returned rows do not establish inspection.')
        row['actions'] = row['actions'][:MAX_ACTIONS]
        result['questions'].append(row)
    counts['questions'] = len(questions)
    result['counts'] = counts
    return result
