"""Public claim-role requirements, not a proof of question entailment.

The contract author declares which existing claim roles can supply an answer
field. No answer key, source values, English inference or Lean calls are used.
Unannotated contracts retain their existing behavior.
"""
from copy import deepcopy
import re
import json

from checker.catalog import ROLES

KEY = 'x-claim-requirement'
ROW_KEY = 'x-claim-row'
SCOPE_KEY = 'x-claim-scope'
ORIGIN_KEYS = ('image', 'exhibit', 'source_snapshot', 'source_variant')
SCOPE = ('Checks compatibility with declared public claim roles and same-part attribute and named field conditions. The requirement itself '
         'needs review; compatibility does not prove question relevance, completeness or truth.')


def _name(value):
    return isinstance(value, str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,127}', value) is not None


def parse(raw):
    allowed = {'semantic_types', 'selectors', 'meaning', 'evidence_needed', 'attribute_conditions', 'field_conditions', 'required_attribute_roles'}
    if not isinstance(raw, dict) or set(raw) - allowed:
        raise ValueError('invalid_public_claim_requirement')
    types = raw.get('semantic_types')
    if (not isinstance(types, list) or not 1 <= len(types) <= 32
            or any(not _name(value) for value in types) or len(set(types)) != len(types)):
        raise ValueError('invalid_public_claim_requirement_types')
    for key in ('meaning', 'evidence_needed'):
        if not isinstance(raw.get(key), str) or not 1 <= len(raw[key].strip()) <= 2000:
            raise ValueError('invalid_public_claim_requirement_description')
    if 'selectors' in raw:
        selectors = raw['selectors']
        if (not isinstance(selectors, list) or not 1 <= len(selectors) <= 64
                or any(not isinstance(row, dict) or set(row) != {'form', 'field'}
                       or not _name(row['form']) or not _name(row['field']) for row in selectors)
                or len({(row['form'], row['field']) for row in selectors}) != len(selectors)):
            raise ValueError('invalid_public_claim_requirement_selectors')
    if 'attribute_conditions' in raw:
        conditions = raw['attribute_conditions']
        if not isinstance(conditions, list) or not 1 <= len(conditions) <= 8:
            raise ValueError('invalid_public_claim_requirement_attribute_conditions')
        seen = set()
        for condition in conditions:
            if not isinstance(condition, dict) or set(condition) != {'role', 'values'}:
                raise ValueError('invalid_public_claim_requirement_attribute_conditions')
            role = condition['role']
            if not isinstance(role, str) or role not in ROLES or role in seen:
                raise ValueError('invalid_public_claim_requirement_attribute_conditions')
            seen.add(role)
            values = condition['values']
            if not isinstance(values, list) or not 1 <= len(values) <= 32 or any(
                    not _native_literal(value, ROLES[role].value_type) for value in values):
                raise ValueError('invalid_public_claim_requirement_attribute_conditions')
    if 'required_attribute_roles' in raw:
        roles = raw['required_attribute_roles']
        if (not isinstance(roles, list) or not 1 <= len(roles) <= 8
                or any(not isinstance(role, str) or role not in ROLES for role in roles)
                or len(set(roles)) != len(roles)):
            raise ValueError('invalid_public_claim_requirement_required_attribute_roles')
    if 'field_conditions' in raw:
        conditions = raw['field_conditions']
        if not isinstance(conditions, list) or not 1 <= len(conditions) <= 8:
            raise ValueError('invalid_public_claim_requirement_field_conditions')
        seen = set()
        for condition in conditions:
            if (not isinstance(condition, dict) or set(condition) != {'field', 'semantic_type', 'values'}
                    or not _name(condition.get('field')) or not _name(condition.get('semantic_type'))
                    or condition['field'] in seen):
                raise ValueError('invalid_public_claim_requirement_field_conditions')
            seen.add(condition['field'])
            values = condition['values']
            if (not isinstance(values, list) or not 1 <= len(values) <= 32
                    or any(not _condition_literal(value) for value in values)):
                raise ValueError('invalid_public_claim_requirement_field_conditions')
    return deepcopy(raw)


def _condition_literal(value):
    return ((type(value) is str and len(value) <= 2000) or type(value) is bool
            or (type(value) is int and value >= 0))


def _native_literal(value, kind):
    return (type(value) is str and len(value) <= 2000 if kind == 'string' else
            type(value) is int and value >= 0 if kind == 'integer' else
            type(value) is bool if kind == 'boolean' else False)


def _literal_key(value):
    return json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(',', ':'))


def compatible(requirement, form, field, semantic_type):
    return (semantic_type in requirement['semantic_types']
            and ('selectors' not in requirement
                 or {'form': form, 'field': field} in requirement['selectors']))


def check(raw, form, field, semantic_type, *, part_fields=None):
    requirement = parse(raw)
    result = {'status': 'compatible' if compatible(requirement, form, field, semantic_type) else 'incompatible',
              'requirement': requirement,
              'offered': {'form': form, 'field': field, 'semantic_type': semantic_type},
              'scope': SCOPE}
    if result['status'] != 'compatible':
        return result
    fields = part_fields if isinstance(part_fields, dict) else {}
    for condition in requirement.get('attribute_conditions', []):
        role = ROLES[condition['role']]
        matches = [(name, row) for name, row in fields.items()
                   if isinstance(row, dict) and row.get('semantic_type') == role.semantic_type]
        diagnostic = {'role': condition['role'], 'values': deepcopy(condition['values']),
                      'matching_fields': [name for name, _ in matches]}
        if not matches:
            diagnostic['status'] = 'missing'
        elif len(matches) != 1:
            diagnostic['status'] = 'ambiguous'
        else:
            value = matches[0][1].get('value')
            diagnostic['offered_value'] = deepcopy(value)
            diagnostic['status'] = ('compatible' if _native_literal(value, role.value_type)
                                    and _literal_key(value) in [_literal_key(option) for option in condition['values']]
                                    else 'incompatible')
        result.setdefault('condition_checks', []).append(diagnostic)
        if diagnostic['status'] != 'compatible':
            result['status'] = 'incompatible'
            result['reason'] = 'claim_attributes_do_not_meet_public_requirement'
    for name in requirement.get('required_attribute_roles', []):
        role = ROLES[name]
        matches = [field_name for field_name, row in fields.items()
                   if isinstance(row, dict) and row.get('semantic_type') == role.semantic_type]
        diagnostic = {'role': name, 'matching_fields': matches,
                      'status': 'compatible' if len(matches) == 1 else 'missing' if not matches else 'ambiguous'}
        result.setdefault('required_attribute_role_checks', []).append(diagnostic)
        if diagnostic['status'] != 'compatible':
            result['status'] = 'incompatible'
            result['reason'] = 'claim_attributes_do_not_meet_public_requirement'
    for condition in requirement.get('field_conditions', []):
        offered = fields.get(condition['field'])
        diagnostic = {'field': condition['field'], 'semantic_type': condition['semantic_type'],
                      'values': deepcopy(condition['values'])}
        if not isinstance(offered, dict) or 'value' not in offered:
            diagnostic['status'] = 'missing'
        elif offered.get('semantic_type') != condition['semantic_type']:
            diagnostic['status'] = 'incompatible_semantic_type'
        else:
            value = offered['value']
            diagnostic['offered_value'] = deepcopy(value)
            diagnostic['status'] = ('compatible' if _condition_literal(value)
                and _literal_key(value) in [_literal_key(option) for option in condition['values']]
                else 'incompatible_value')
        result.setdefault('field_condition_checks', []).append(diagnostic)
        if diagnostic['status'] != 'compatible':
            result['status'] = 'incompatible'
            result['reason'] = 'claim_fields_do_not_meet_public_requirement'
    return result


def _semantic_types(spec):
    """Expand a reviewed selector's fixed role variants; never infer source meaning."""
    variants = spec.get('allowed_semantic_types')
    if variants is None:
        return [spec['semantic_type']]
    if (not isinstance(variants, list) or not 1 <= len(variants) <= 128
            or any(not _name(value) for value in variants) or len(set(variants)) != len(variants)):
        raise ValueError('invalid_catalog_semantic_type_variants')
    return variants


def parse_scope(raw):
    if not isinstance(raw, dict):
        raise ValueError('invalid_public_claim_scope_requirement')
    if raw.get('mode') in ('unscoped_observation', 'unavailable'):
        if set(raw) != {'mode', 'meaning'} or not isinstance(raw['meaning'], str) or not 1 <= len(raw['meaning'].strip()) <= 2000:
            raise ValueError('invalid_public_claim_scope_requirement')
    elif raw.get('mode') == 'source_records':
        if set(raw) - {'mode', 'origins', 'evidence_facts_sha256', 'same_origin'}:
            raise ValueError('invalid_public_claim_scope_requirement')
        if 'same_origin' in raw and type(raw['same_origin']) is not bool:
            raise ValueError('invalid_public_claim_scope_requirement')
        origins = raw.get('origins')
        if not isinstance(origins, list) or not 1 <= len(origins) <= 64:
            raise ValueError('invalid_public_claim_scope_requirement')
        for origin in origins:
            if not isinstance(origin, dict) or set(origin) != set(ORIGIN_KEYS) | ({'input_source'} if origin.get('source_snapshot') == 'examination' else set()) or any(
                    not isinstance(origin[key], str) or not 1 <= len(origin[key].strip()) <= 2000 or '*' in origin[key]
                    for key in ORIGIN_KEYS):
                raise ValueError('invalid_public_claim_scope_requirement')
            if any(origin[key].strip().lower() == 'unknown' for key in ORIGIN_KEYS):
                raise ValueError('invalid_public_claim_scope_requirement')
            if origin['source_snapshot'] == 'examination':
                input_source = origin['input_source']
                if origin['source_variant'] != 'antivirus' or not isinstance(input_source, dict) or set(input_source) != {'source_snapshot', 'source_variant'} or any(
                        not isinstance(value, str) or not 1 <= len(value.strip()) <= 2000 or '*' in value or value.strip().lower() == 'unknown'
                        for value in input_source.values()):
                    raise ValueError('invalid_public_claim_scope_requirement')
        if 'evidence_facts_sha256' in raw and not valid_facts_digest(raw['evidence_facts_sha256']):
            raise ValueError('invalid_public_claim_scope_requirement')
    else:
        raise ValueError('invalid_public_claim_scope_requirement')
    return deepcopy(raw)


def valid_facts_digest(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def applicable_scopes(schema, path, *, require_evidence_scope=False):
    """Resolve inherited conjunctions in every alternative without branch choice."""
    pending, found, visited, applicable = [([schema], 0, [], 0)], [], 0, 0
    while pending:
        nodes, position, inherited, depth = pending.pop()
        visited += len(nodes)
        if visited > 256 or depth > 32:
            raise ValueError('public_schema_traversal_limit')
        scopes = list(inherited)
        expanded = False
        for index, node in enumerate(nodes):
            if not isinstance(node, dict):
                raise ValueError('unsupported_public_schema_node')
            if any(key in node for key in ('$ref', '$dynamicRef', '$recursiveRef', 'oneOf', 'allOf')):
                raise ValueError('unsupported_schema_reference_or_union')
            if 'anyOf' in node:
                alternatives = node['anyOf']
                if not isinstance(alternatives, list) or not 1 <= len(alternatives) <= 32:
                    raise ValueError('unsupported_public_schema_anyof')
                siblings = {key: value for key, value in node.items() if key != 'anyOf'}
                for branch in reversed(alternatives):
                    pending.append((nodes[:index] + [siblings, branch] + nodes[index + 1:], position, inherited, depth + 1))
                expanded = True
                break
        if expanded:
            continue
        for node in nodes:
            if SCOPE_KEY in node:
                scope = parse_scope(node[SCOPE_KEY])
                if scope not in scopes:
                    scopes.append(scope)
        if position == len(path):
            applicable += 1
            if require_evidence_scope and not scopes:
                raise ValueError('missing_public_claim_scope_requirement')
            for scope in scopes:
                if scope not in found:
                    found.append(scope)
            continue
        children = []
        try:
            for node in nodes:
                token = path[position]
                kind = node.get('type')
                allowed = kind if isinstance(kind, list) else [kind] if kind else []
                if type(token) is int:
                    if allowed and 'array' not in allowed:
                        raise ValueError('array_path_does_not_match_public_schema')
                    child = node.get('items', {})
                else:
                    if allowed and 'object' not in allowed:
                        raise ValueError('object_path_does_not_match_public_schema')
                    properties = node.get('properties', {})
                    if not isinstance(properties, dict):
                        raise ValueError('unsupported_public_schema_node')
                    child = properties.get(token, node.get('additionalProperties', {}))
                    if child is False:
                        raise ValueError('field_not_in_public_schema')
                    if child is True:
                        child = {}
                children.append(child)
        except ValueError as error:
            # Closed alternative-exclusive paths are not ambiguous meanings of
            # this leaf. Discard this whole conjunction, never its constraints.
            if str(error) in ('field_not_in_public_schema', 'object_path_does_not_match_public_schema',
                              'array_path_does_not_match_public_schema'):
                continue
            raise
        pending.append((children, position + 1, scopes, depth + 1))
    if not applicable:
        raise ValueError('field_not_in_public_schema')
    return found


def scope_requirements(schema, *, require_evidence_scope=False):
    if type(require_evidence_scope) is not bool:
        raise ValueError('require_evidence_scope must be a boolean')
    if not require_evidence_scope:
        try:
            if '"x-claim-scope":' not in json.dumps(schema, separators=(',', ':')):
                return [], []
        except (ValueError, TypeError, RecursionError):
            pass
    pending, rows, errors, paths, visited = [(schema, [], [], 0)], [], [], [], 0
    while pending:
        node, path, branches, depth = pending.pop()
        visited += 1
        if visited > 256 or depth > 32:
            errors.append({'path': path, 'status': 'invalid', 'reason': 'public_schema_traversal_limit'})
            break
        if not isinstance(node, dict):
            continue
        if SCOPE_KEY in node:
            row = {'path': path, 'branches': branches}
            try:
                scope = parse_scope(node[SCOPE_KEY])
                rows.append(dict(row, status='unavailable' if scope['mode'] == 'unavailable' else 'valid', requirement=scope))
            except ValueError as error:
                errors.append(dict(row, status='invalid', reason=str(error)))
        properties = node.get('properties', {})
        children = []
        if isinstance(properties, dict):
            children.extend((child, path + [name], branches, depth + 1) for name, child in properties.items())
        if 'items' in node:
            children.append((node['items'], path + ['*'], branches, depth + 1))
        if isinstance(node.get('additionalProperties'), dict):
            children.append((node['additionalProperties'], path + [{'additional_property': True}], branches, depth + 1))
        alternatives = node.get('anyOf', [])
        if 'anyOf' in node and (not isinstance(alternatives, list) or not 1 <= len(alternatives) <= 32):
            errors.append({'path': path, 'status': 'invalid', 'reason': 'unsupported_public_schema_anyof'})
            continue
        children.extend((child, path, branches + [index], depth + 1) for index, child in enumerate(alternatives))
        if not children and node.get('type') not in ('object', 'array'):
            paths.append(path)
        if visited + len(pending) + len(children) > 256:
            errors.append({'path': path, 'status': 'invalid', 'reason': 'public_schema_traversal_limit'})
            break
        pending.extend(reversed(children))
    if require_evidence_scope:
        for path in paths:
            sample = '__scope_additional_property__'
            while sample in repr(schema):
                sample += '_'
            actual = [0 if token == '*' else sample if isinstance(token, dict) else token for token in path]
            try:
                applicable_scopes(schema, actual, require_evidence_scope=True)
            except (ValueError, TypeError, KeyError) as error:
                row = {'path': path, 'status': 'invalid', 'reason': str(error)}
                if row not in errors:
                    errors.append(row)
    return rows, errors


def row_requirements(schema, *, require_claim_requirements=False):
    """Bounded, evidence-free validation of explicit object coherence policies."""
    if type(require_claim_requirements) is not bool:
        raise ValueError('require_claim_requirements must be a boolean')
    # JSON token search only selects whether to apply the bounded row walker.
    # Escaped text values cannot impersonate a key token. Legacy contracts
    # without explicit row policy retain their existing per-path limits.
    if not require_claim_requirements:
        try:
            if '"x-claim-row":' not in json.dumps(schema, separators=(',', ':')):
                return [], []
        except (ValueError, TypeError, RecursionError):
            pass
    objects = {}
    pending, rows, errors, visited = [(schema, [], [], 0)], [], [], 0
    while pending:
        node, path, branches, depth = pending.pop()
        visited += 1
        if visited > 256 or depth > 32:
            errors.append({'path': path, 'status': 'invalid', 'reason': 'public_schema_traversal_limit'})
            break
        if not isinstance(node, dict):
            continue
        if ROW_KEY in node:
            raw = node[ROW_KEY]
            reason = None
            if not isinstance(raw, dict) or set(raw) != {'mode'} or raw['mode'] not in ('same_claim_part', 'independent'):
                reason = 'invalid_public_claim_row_requirement'
            else:
                kind = node.get('type')
                object_type = kind == 'object' or (isinstance(kind, list) and 'object' in kind and all(item in ('object', 'null') for item in kind))
                if not object_type and not (kind is None and isinstance(node.get('properties'), dict)):
                    reason = 'claim_row_requirement_must_annotate_object'
            row = {'path': path, 'branches': branches}
            if reason:
                errors.append(dict(row, status='invalid', reason=reason))
            else:
                rows.append(dict(row, status='valid', mode=raw['mode']))
        alternatives = node.get('anyOf', [])
        if 'anyOf' in node and (not isinstance(alternatives, list) or not 1 <= len(alternatives) <= 32):
            errors.append({'path': path, 'status': 'invalid', 'reason': 'unsupported_public_schema_anyof'})
            continue
        properties = node.get('properties', {})
        path_key = json.dumps(path, sort_keys=True)
        obj = objects.setdefault(path_key, {'path': path, 'nodes': []})
        obj['nodes'].append((branches, set(properties) if isinstance(properties, dict) else set(),
                             isinstance(node.get('additionalProperties'), dict)))
        children = []
        if isinstance(properties, dict):
            children.extend((child, path + [name], branches, depth + 1) for name, child in properties.items())
        if 'items' in node:
            children.append((node['items'], path + ['*'], branches, depth + 1))
        additional = node.get('additionalProperties')
        if isinstance(additional, dict):
            marker = {'additional_property': True, 'excluded_properties': list(properties) if isinstance(properties, dict) else []}
            children.append((additional, path + [marker], branches, depth + 1))
        children.extend((child, path, branches + [index], depth + 1) for index, child in enumerate(alternatives))
        if visited + len(pending) + len(children) > 256:
            errors.append({'path': path, 'status': 'invalid', 'reason': 'public_schema_traversal_limit'})
            break
        pending.extend(reversed(children))
    if require_claim_requirements:
        for key, obj in objects.items():
            # Open alternatives can each permit keys declared by another
            # alternative. The projector can therefore retain their union.
            properties = set().union(*(names for _, names, _ in obj['nodes']))
            additional = any(extra for _, _, extra in obj['nodes'])
            if len(properties) <= 1 and not additional:
                continue
            contexts = [branch for branch, _, _ in obj['nodes']]
            # A sibling declaration applies to every alternative below it;
            # one alternative's declaration never licenses another alternative.
            terminal_contexts = [branch for branch in contexts if not any(
                len(other) > len(branch) and other[:len(branch)] == branch for other in contexts)]
            declarations = [row['branches'] for row in rows
                            if json.dumps(row['path'], sort_keys=True) == key]
            for branch in terminal_contexts:
                if not any(branch[:len(declaration)] == declaration for declaration in declarations):
                    errors.append({'path': obj['path'], 'branches': branch, 'status': 'invalid',
                                   'reason': 'missing_public_claim_row_requirement'})
    return rows, errors


def inspect(schema, forms, *, require_claim_requirements=False, require_evidence_scope=False):
    """Bounded preflight of public annotations; available roles are not evidence.

    Paths use '*' for an array item and {'additional_property': True} for a
    schema-valued additional property. Alternatives are shown separately. Actual
    bindings must satisfy all leaf requirements reached by the shared projector.
    """
    if type(require_claim_requirements) is not bool:
        raise ValueError('require_claim_requirements must be a boolean')
    pending, rows, visited = [(schema, [], [], 0)], [], 0
    while pending:
        node, path, branches, depth = pending.pop()
        visited += 1
        if visited > 4096 or depth > 32:
            rows.append({'path': path, 'status': 'invalid', 'reason': 'requirement_preflight_limit'})
            break
        if not isinstance(node, dict):
            continue
        if any(key in node for key in ('$ref', '$dynamicRef', '$recursiveRef', 'oneOf', 'allOf')):
            rows.append({'path': path, 'status': 'invalid', 'reason': 'unsupported_schema_reference_or_union'})
            continue
        if require_claim_requirements and KEY not in node and not any(key in node for key in ('properties', 'items', 'additionalProperties', 'anyOf')) and node.get('type') not in ('object', 'array'):
            rows.append({'path': path, 'branches': branches, 'status': 'missing_annotation', 'reason': 'missing_public_claim_requirement'})
        if require_claim_requirements and 'anyOf' in node and (not isinstance(node['anyOf'], list) or not 1 <= len(node['anyOf']) <= 32):
            rows.append({'path': path, 'branches': branches, 'status': 'invalid', 'reason': 'unsupported_public_schema_anyof'})
            continue
        if require_claim_requirements and KEY in node and (any(key in node for key in ('properties', 'items', 'additionalProperties', 'prefixItems')) or node.get('type') in ('object', 'array')):
            rows.append({'path': path, 'branches': branches, 'status': 'invalid', 'reason': 'claim_requirement_must_annotate_exact_answer_value'})
            continue
        if KEY in node:
            row = {'path': path, 'branches': branches}
            try:
                requirement = parse(node[KEY])
                available = [{'form': form, 'field': field, 'semantic_type': semantic_type}
                             for form, fields in forms.items() for field, spec in fields.items()
                             for semantic_type in _semantic_types(spec)
                             if compatible(requirement, form, field, semantic_type)]
                row.update(requirement=requirement, available_fields=available,
                           status='catalog_support' if available else 'no_catalog_support')
            except ValueError as error:
                row.update(status='invalid', reason=str(error))
            rows.append(row)
        properties = node.get('properties', {})
        alternatives = node.get('anyOf', [])
        additional = node.get('additionalProperties')
        children = ((len(properties) if isinstance(properties, dict) else 0)
                    + (len(alternatives) if isinstance(alternatives, list) else 0)
                    + int('items' in node) + int(isinstance(additional, dict)))
        if visited + len(pending) + children > 4096:
            rows.append({'path': path, 'status': 'invalid', 'reason': 'requirement_preflight_limit'})
            break
        if isinstance(properties, dict):
            pending.extend((child, path + [name], branches, depth + 1)
                           for name, child in reversed(list(properties.items())))
        if 'items' in node:
            pending.append((node['items'], path + ['*'], branches, depth + 1))
        if isinstance(additional, dict):
            pending.append((additional, path + [{'additional_property': True}], branches, depth + 1))
        if isinstance(alternatives, list):
            pending.extend((child, path, branches + [i], depth + 1)
                           for i, child in reversed(list(enumerate(alternatives))))
    if require_claim_requirements:
        # Structural anyOf siblings are conjunctive; an annotation on their
        # shared leaf applies to each alternative. Use the binding resolver.
        from agent.answer_projection import _strict_schema
        filtered = []
        for row in rows:
            if row.get('status') == 'missing_annotation':
                try:
                    # Resolve wildcard paths with a representative array index
                    # or an object key absent from all declared properties.
                    sample = '__claim_requirement_additional_property__'
                    while sample in repr(schema):
                        sample += '_'
                    path = [0 if token == '*' else sample if isinstance(token, dict) else token
                            for token in row['path']]
                    _strict_schema(schema, path)
                    continue
                except (ValueError, TypeError, KeyError):
                    pass
            filtered.append(row)
        rows = filtered
    row_policies, row_errors = row_requirements(schema, require_claim_requirements=require_claim_requirements)
    # A policy hidden beyond the scan budget cannot be treated as absent.
    rows.extend(row_errors)
    scope_policies, scope_errors = scope_requirements(schema, require_evidence_scope=require_evidence_scope)
    rows.extend(scope_errors)
    from agent import answer_references
    reference_policies, reference_errors = answer_references.inspect_schema(schema)
    rows.extend(reference_errors)
    return {'requirements': rows, 'row_requirements': row_policies, 'scope_requirements': scope_policies,
            'reference_requirements': reference_policies, 'scope': SCOPE,
            'unannotated_fields': ('Unannotated answer fields are blocked by strict claim-role policy.'
                                   if require_claim_requirements else
                                   'No declared claim-role requirement; question placement remains unchecked.')}
