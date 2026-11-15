"""Public cross-question atomic-part dependencies, frozen before admission gates."""
from collections import defaultdict, deque
from copy import deepcopy
import json

KEY = 'x-claim-reference'
MAX_BINDINGS = 20000
MAX_NODES = 4096


def _path(path):
    return (isinstance(path, list) and len(path) <= 16 and all(
        type(token) is str and 0 < len(token) <= 200 or
        type(token) is int and 0 <= token <= 100000 for token in path))


def parse(raw):
    if (not isinstance(raw, dict) or set(raw) != {'mode', 'question_id', 'path'}
            or raw['mode'] != 'same_claim_part' or not isinstance(raw['question_id'], str)
            or not 1 <= len(raw['question_id']) <= 128 or not _path(raw['path'])):
        raise ValueError('invalid_public_claim_reference')
    return deepcopy(raw)


def inspect_schema(schema):
    """Local preflight only; public target existence needs validate_public."""
    try:
        if '"x-claim-reference":' not in json.dumps(schema, separators=(',', ':')):
            return [], []
    except (ValueError, TypeError, RecursionError):
        pass
    pending, rows, errors, visited = [(schema, [], 0)], [], [], 0
    while pending:
        node, path, depth = pending.pop()
        visited += 1
        if visited > MAX_NODES or depth > 32:
            errors.append({'path': path, 'status': 'invalid', 'reason': 'public_claim_reference_traversal_limit'})
            break
        if not isinstance(node, dict):
            continue
        if KEY in node:
            try:
                requirement = parse(node[KEY])
                if any(key in node for key in ('properties', 'items', 'additionalProperties', 'anyOf')) or node.get('type') in ('object', 'array'):
                    raise ValueError('claim_reference_must_annotate_exact_answer_value')
                rows.append({'path': path, 'status': 'valid', 'requirement': requirement})
            except ValueError as error:
                errors.append({'path': path, 'status': 'invalid', 'reason': str(error)})
        children = []
        properties = node.get('properties', {})
        if isinstance(properties, dict):
            children.extend((child, path + [name], depth + 1) for name, child in properties.items())
        if 'items' in node:
            children.append((node['items'], path + ['*'], depth + 1))
        if isinstance(node.get('additionalProperties'), dict):
            children.append((node['additionalProperties'], path + [{'additional_property': True}], depth + 1))
        alternatives = node.get('anyOf', [])
        if not isinstance(alternatives, list) or len(alternatives) > 32:
            errors.append({'path': path, 'status': 'invalid', 'reason': 'invalid_public_claim_reference_schema'})
            continue
        children.extend((child, path, depth + 1) for child in alternatives)
        if visited + len(pending) + len(children) > MAX_NODES:
            errors.append({'path': path, 'status': 'invalid', 'reason': 'public_claim_reference_traversal_limit'})
            break
        pending.extend(reversed(children))
    counts = defaultdict(int)
    for row in rows:
        key = json.dumps(row['path'], sort_keys=True)
        counts[key] += 1
        if counts[key] > 8:
            errors.append(dict(row, status='invalid', reason='public_claim_reference_leaf_limit'))
    return rows, errors


def _target_exists(schema, path):
    pending, visited = [(schema, 0, 0)], 0
    while pending:
        node, position, depth = pending.pop()
        visited += 1
        if visited > MAX_NODES or depth > 32:
            raise ValueError('public_claim_reference_traversal_limit')
        if not isinstance(node, dict):
            continue
        if any(key in node for key in ('$ref', '$dynamicRef', '$recursiveRef', 'oneOf', 'allOf')):
            raise ValueError('unsupported_public_claim_reference_target')
        if position == len(path):
            if not any(key in node for key in ('properties', 'items', 'anyOf', 'additionalProperties')) and node.get('type') not in ('object', 'array'):
                return True
        alternatives = node.get('anyOf', [])
        if not isinstance(alternatives, list) or len(alternatives) > 32:
            raise ValueError('invalid_public_claim_reference_schema')
        pending.extend((child, position, depth + 1) for child in alternatives)
        if position < len(path):
            token = path[position]
            if type(token) is int:
                child = node.get('items')
            else:
                properties = node.get('properties', {})
                child = properties.get(token) if isinstance(properties, dict) else None
            if child is not None:
                pending.append((child, position + 1, depth + 1))
    return False


def _cycle_nodes(graph):
    """Identify actual cycle members with a bounded iterative DFS."""
    done, cyclic = set(), set()
    for start in graph:
        if start in done:
            continue
        active, positions = [start], {start: 0}
        stack = [(start, iter(graph.get(start, ())))]
        while stack:
            node, children = stack[-1]
            target = next(children, None)
            if target is None:
                stack.pop(); active.pop(); positions.pop(node); done.add(node)
            elif target in positions:
                cyclic.update(active[positions[target]:])
            elif target not in done:
                positions[target] = len(active); active.append(target)
                stack.append((target, iter(graph.get(target, ()))))
    return cyclic


def validate_public(public):
    questions = public.get('questions') if isinstance(public, dict) else None
    if not isinstance(questions, list) or len(questions) > 2000:
        raise ValueError('invalid_public_claim_reference_contract')
    indexed, rows, errors = {}, [], []
    for question in questions:
        if not isinstance(question, dict) or not isinstance(question.get('id'), str) or question['id'] in indexed:
            raise ValueError('invalid_public_claim_reference_contract')
        indexed[question['id']] = question.get('answer_schema')
    edges = defaultdict(set)
    for qid, schema in indexed.items():
        local, invalid = inspect_schema(schema)
        rows.extend(dict(row, question_id=qid) for row in local)
        errors.extend(dict(row, question_id=qid) for row in invalid)
        if len(rows) + len(errors) > MAX_BINDINGS:
            raise ValueError('public_claim_reference_traversal_limit')
        for row in local:
            reference = row['requirement']
            target = reference['question_id']
            reason = None
            if target == qid:
                reason = 'self_public_claim_reference'
            elif target not in indexed:
                reason = 'dangling_public_claim_reference'
            else:
                try:
                    if not _target_exists(indexed[target], reference['path']):
                        reason = 'dangling_public_claim_reference'
                except ValueError as error:
                    reason = str(error)
            if reason:
                errors.append(dict(row, question_id=qid, status='invalid', reason=reason))
            else:
                edges[qid].add(target)
    cyclic = _cycle_nodes(edges)
    for row in rows:
        if row['question_id'] in cyclic and row['requirement']['question_id'] in cyclic:
            errors.append(dict(row, status='invalid', reason='cyclic_public_claim_reference'))
    return {'reference_requirements': rows, 'errors': errors}


def freeze_references(plan):
    entries = plan.get('bindings')
    if not isinstance(entries, list) or len(entries) > MAX_BINDINGS:
        raise ValueError('invalid_frozen_answer_references')
    seen = set()
    for entry in entries:
        if (not isinstance(entry, dict) or type(entry.get('binding_index')) is not int
                or entry['binding_index'] < 0 or entry['binding_index'] in seen
                or not isinstance(entry.get('candidate_id'), str)
                or type(entry.get('part')) is not int or entry['part'] < 0
                or not isinstance(entry.get('question_id'), str) or not _path(entry.get('path'))):
            raise ValueError('invalid_frozen_answer_references')
        seen.add(entry['binding_index'])
    conflicts = plan.setdefault('frozen_conflicts', [])
    blocked = {index for conflict in conflicts for index in conflict['binding_indices']}
    targets, dependents, failures = defaultdict(list), defaultdict(list), []
    for entry in entries:
        targets[(entry['question_id'], json.dumps(entry['path']))].append(entry)
    for entry in entries:
        refs = entry.get('answer_references', [])
        if not isinstance(refs, list) or len(refs) > 8:
            raise ValueError('invalid_frozen_answer_references')
        for raw in refs:
            reference = parse(raw)
            candidates = targets[(reference['question_id'], json.dumps(reference['path']))]
            surviving = [target for target in candidates if target['binding_index'] not in blocked]
            status = None
            if len(candidates) > 1:
                status = 'duplicate'
            elif not surviving:
                status = 'conflicted' if candidates else 'absent'
            else:
                target = surviving[0]
                if (target['candidate_id'], target['part']) != (entry['candidate_id'], entry['part']):
                    status = 'different_claim_part'
                else:
                    dependents[target['binding_index']].append((entry, reference))
            if status:
                failures.append((entry, reference, status))
    graph = defaultdict(set)
    for target_index, linked in dependents.items():
        for entry, _ in linked:
            graph[entry['binding_index']].add(target_index)
    cyclic = _cycle_nodes(graph)
    for target_index, linked in dependents.items():
        for entry, reference in linked:
            if entry['binding_index'] in cyclic and target_index in cyclic:
                failures.append((entry, reference, 'cyclic'))
    queue = deque()
    def refuse(entry, reference, status):
        index = entry['binding_index']
        if index in blocked:
            return
        blocked.add(index); queue.append(index)
        conflicts.append({'reason': 'answer_reference_requires_same_claim_part', 'binding_indices': [index],
                          'question_id': entry['question_id'], 'path': deepcopy(entry['path']),
                          'target_question_id': reference['question_id'], 'target_path': deepcopy(reference['path']),
                          'reference_status': status})
    for entry, reference, status in failures:
        refuse(entry, reference, status)
    while queue:
        target_index = queue.popleft()
        for entry, reference in dependents[target_index]:
            refuse(entry, reference, 'conflicted')
    return plan
