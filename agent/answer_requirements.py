"""Public claim-role requirements, not a proof of question entailment.

The contract author declares which existing claim roles can supply an answer
field. No answer key, source values, English inference or Lean calls are used.
Unannotated contracts retain their existing behavior.
"""
from copy import deepcopy
import re

KEY = 'x-claim-requirement'
SCOPE = ('Checks compatibility with declared public claim roles only. The requirement itself '
         'needs review; compatibility does not prove question relevance, completeness or truth.')


def _name(value):
    return isinstance(value, str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,127}', value) is not None


def parse(raw):
    allowed = {'semantic_types', 'selectors', 'meaning', 'evidence_needed'}
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
    return deepcopy(raw)


def compatible(requirement, form, field, semantic_type):
    return (semantic_type in requirement['semantic_types']
            and ('selectors' not in requirement
                 or {'form': form, 'field': field} in requirement['selectors']))


def check(raw, form, field, semantic_type):
    requirement = parse(raw)
    return {'status': 'compatible' if compatible(requirement, form, field, semantic_type) else 'incompatible',
            'requirement': requirement,
            'offered': {'form': form, 'field': field, 'semantic_type': semantic_type},
            'scope': SCOPE}


def _semantic_types(spec):
    """Expand a reviewed selector's fixed role variants; never infer source meaning."""
    variants = spec.get('allowed_semantic_types')
    if variants is None:
        return [spec['semantic_type']]
    if (not isinstance(variants, list) or not 1 <= len(variants) <= 128
            or any(not _name(value) for value in variants) or len(set(variants)) != len(variants)):
        raise ValueError('invalid_catalog_semantic_type_variants')
    return variants


def inspect(schema, forms):
    """Bounded preflight of public annotations; available roles are not evidence.

    Paths use '*' for an array item and {'additional_property': True} for a
    schema-valued additional property. Alternatives are shown separately. Actual
    bindings must satisfy all leaf requirements reached by the shared projector.
    """
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
    return {'requirements': rows, 'scope': SCOPE,
            'unannotated_fields': 'No declared claim-role requirement; question placement remains unchecked.'}
