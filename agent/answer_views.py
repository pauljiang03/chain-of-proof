"""Bounded native tool views; durable answer bindings and projections stay complete."""
from __future__ import annotations

import hashlib
import json

SECTIONS = ('bindings', 'leaves', 'unsupported', 'conflicts', 'field_requirements', 'field_catalog', 'answers')
DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100
MAX_ITEM_BYTES = 4096
MAX_PAGE_BYTES = 48_000
MAX_RESPONSE_BYTES = 64_000
SAMPLE_SIZE = 5


def _encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode()


def _digest(value):
    return hashlib.sha256(_encoded(value)).hexdigest()


def validate_request(bindings, replace=False, preview=False, *, section=None, offset=None,
                     page_size=None, state_token=None):
    """Validate before entering the mutating store, including preview-error paths."""
    if type(replace) is not bool or type(preview) is not bool:
        raise ValueError('replace and preview must be Booleans')
    if preview and bindings is None:
        raise ValueError('answer preview requires a bindings list')
    paging = any(value is not None for value in (section, offset, page_size, state_token))
    if paging and (bindings is not None or replace or preview):
        raise ValueError('answer paging parameters are inspection-only; omit bindings, replace and preview')
    if section is not None and section not in SECTIONS:
        raise ValueError('unsupported answer inspection section')
    if offset is not None and (type(offset) is not int or offset < 0):
        raise ValueError('answer offset must be a nonnegative integer')
    if page_size is not None and (type(page_size) is not int or not 1 <= page_size <= MAX_PAGE_SIZE):
        raise ValueError(f'answer page_size must be an integer from 1 to {MAX_PAGE_SIZE}')
    if state_token is not None and (not isinstance(state_token, str) or len(state_token) != 64
                                    or any(c not in '0123456789abcdef' for c in state_token)):
        raise ValueError('answer state_token must be a SHA-256 token returned by inspection')
    if offset and state_token is None:
        raise ValueError('answer continuation requires the returned state_token')


def bounded(value):
    """An oversize value is explicitly a descriptor, never an exact clipped value."""
    raw = _encoded(value)
    if len(raw) <= MAX_ITEM_BYTES:
        return value
    descriptor = {'view': 'omitted_oversize_value', 'exact_value_included': False,
                  'json_bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                  'preview': raw[:768].decode('ascii'), 'preview_is_exact_value': False,
                  'full_value_location': 'complete durable answer state; this is a tool-facing preview only'}
    if isinstance(value, dict):
        # Preserve short record locators outside the preview so a large leaf's
        # content cannot hide which binding/answer location the page describes.
        identity = {key: item for key, item in value.items()
                    if key in ('candidate_id', 'question_id', 'binding_index', 'part', 'field',
                               'path', 'status', 'reason', 'semantic_type')
                    and len(_encoded(item)) <= 256}
        if identity:
            descriptor['record_identity'] = identity
    return descriptor


def _page(rows, offset, page_size, token):
    if offset > len(rows):
        raise ValueError('answer offset exceeds section total')
    items, used = [], 0
    for row in rows[offset:offset + page_size]:
        item = bounded(row)
        size = len(_encoded(item))
        if items and used + size > MAX_PAGE_BYTES:
            break
        items.append(item)
        used += size
    next_offset = offset + len(items)
    return {'offset': offset, 'page_size': page_size, 'returned': len(items), 'total': len(rows),
            'next_offset': next_offset if next_offset < len(rows) else None,
            'state_token': token, 'items': items, 'bounded_values': True}


def _selected(projection, question_id):
    if projection is None:
        return {'answers': [], 'leaves': [], 'unsupported': [], 'conflicts': []}
    result = {'answers': [a for a in projection.get('submission', {}).get('answers', [])
                          if a.get('question_id') == question_id]}
    for key in ('leaves', 'unsupported', 'conflicts'):
        result[key] = [row for row in projection.get(key, [])
                       if row.get('question_id', row.get('binding', {}).get('question_id')) == question_id]
    return result


def _complete_rows(path, value):
    if len(_encoded({'path': path, 'value': value})) <= MAX_ITEM_BYTES or not isinstance(value, (dict, list)):
        return [{'path': path, 'value': value}]
    children = value.items() if isinstance(value, dict) else enumerate(value)
    return [row for key, child in children for row in _complete_rows(path + [key], child)]


def _catalog_rows(catalog):
    # Each selector and approved role remains inspectable. No repeated expansion
    # of allowed semantic variants is introduced by the native output view.
    rows = []
    for key, value in catalog.items():
        if key == 'forms':
            rows.extend({'path': [key, form, field], 'value': spec}
                        for form, fields in value.items() for field, spec in fields.items())
        elif key == 'attribute_roles':
            rows.extend({'path': [key, role], 'value': spec} for role, spec in value.items())
        else:
            rows.append({'path': [key], 'value': value})
    return [entry for row in rows for entry in _complete_rows(row['path'], row['value'])]


def _requirement_rows(requirements):
    return [entry for key, value in requirements.items()
            for i, row in (enumerate(value) if isinstance(value, list) else [(None, value)])
            for entry in _complete_rows([key] + ([i] if i is not None else []), row)]


def inspection(run_dir, question_id, *, offset=None, page_size=None, section=None, state_token=None,
               _evidence_source=None, _evidence_facts_sha256=None):
    """Read-only, selected-question pages bound to one locked full-state snapshot."""
    from agent.answer_store import _inspection_snapshot
    validate_request(None, section=section, offset=offset, page_size=page_size, state_token=state_token)
    section, offset, page_size = section or 'bindings', offset or 0, page_size or DEFAULT_PAGE_SIZE
    snapshot = _inspection_snapshot(run_dir, question_id, _evidence_source=_evidence_source,
                                    _evidence_facts_sha256=_evidence_facts_sha256)
    before, projection = snapshot['inspection'], snapshot['projection']
    token = _digest(snapshot)
    if state_token is not None and token != state_token:
        raise ValueError('answer state_token is stale or belongs to another question; restart at offset 0')
    rows = _selected(projection, question_id)
    rows.update(bindings=before['bindings'], field_catalog=_catalog_rows(before['field_catalog']),
                field_requirements=_requirement_rows(before['field_requirements']))
    page = _page(rows[section], offset, page_size, token)
    response = {'view': 'bounded_answer_inspection', 'question_id': question_id, 'section': section,
            'state_token': token, 'counts': {key: len(value) for key, value in rows.items()},
            'page': page, section: page['items'],
            'inspection_sections': list(SECTIONS),
            'continuation': 'Omit bindings/replace/preview; use section, next_offset, page_size and this state_token. Each section is separately paged.',
            'value_policy': 'Oversize entries are explicit length/hash/preview descriptors, not exact values. Complete originals remain on disk.',
            'question_completeness': 'not_established'}
    # The compatibility alias repeats items outside page, and ordinary JSON
    # serialization adds spaces. Bound the entire returned envelope, not only
    # its compact item encodings. Removed items remain at the next cursor.
    while len(json.dumps(response, ensure_ascii=True, allow_nan=False).encode('utf-8')) > MAX_RESPONSE_BYTES:
        if not page['items']:
            raise ValueError('answer inspection envelope exceeds response byte limit')
        page['items'].pop()
        page['returned'] = len(page['items'])
        next_offset = offset + page['returned']
        page['next_offset'] = next_offset if next_offset < page['total'] else None
    if rows[section] and offset < len(rows[section]) and not page['returned']:
        raise ValueError('answer inspection entry exceeds response byte limit')
    return response


def mutation_view(result, question_id):
    """Keep selected-Q outcomes and bounded diagnostics, never all-Q projections."""
    projection = result.get('projection') if result.get('preview') else result
    projection = projection if isinstance(projection, dict) else {}
    rows = _selected(projection, question_id)
    out = {'view': 'bounded_answer_update', 'question_id': question_id,
           'preview': bool(result.get('preview', False)),
           'valid': result.get('valid', not projection.get('unsupported') and not projection.get('conflicts')
                               and not result.get('errors')),
           'persisted': result.get('persisted', not result.get('preview', False)),
           'counts': {key: len(value) for key, value in rows.items()},
           'validation_scope': 'all proposed bindings across questions; answer samples and counts are selected-question only',
           'global_diagnostic_counts': {key: len(projection.get(key, [])) for key in ('unsupported', 'conflicts')},
           'submission': {'answers': [bounded(row) for row in rows['answers']]},
           'projection': {key: projection.get('projection', {}).get(key) for key in
                          ('evidence_facts_sha256', 'public_sha256', 'projection_sha256')},
           'question_completeness': 'not_established',
           'inspection': 'For full persisted bindings/leaves/diagnostics, omit bindings and page the selected section with its state_token.',
           'preview_note': 'Preview diagnostics describe the proposed state; inspection always reads persisted state.'}
    for key in ('leaves', 'unsupported', 'conflicts'):
        out[key] = [bounded(row) for row in rows[key][:SAMPLE_SIZE]]
        out[key + '_omitted_count'] = max(0, len(rows[key]) - SAMPLE_SIZE)
    if 'update_outcome' in result:
        out['update_outcome'] = result['update_outcome']
    if 'errors' in result:
        out['errors'] = [bounded(row) for row in result['errors'][:SAMPLE_SIZE]]
        out['errors_omitted_count'] = max(0, len(result['errors']) - SAMPLE_SIZE)
    return out
