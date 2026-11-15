"""Page through the static claim and answer catalogs in bounded, exact pieces."""
from copy import deepcopy
import hashlib
import json

SECTIONS = ('claim_forms', 'answer_fields', 'attribute_roles', 'metadata')
DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100
MAX_RESPONSE_BYTES = 64000
MAX_ITEM_BYTES = 4096
VERSION = 1


def _encoded(value):
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode('ascii')
    except (ValueError, TypeError, RecursionError) as error:
        raise ValueError('static catalog must contain bounded finite JSON') from error


def _catalogs():
    from agent.tools import Workbench
    from agent.answer_projection import tool_catalog
    claim, answer = Workbench.forms.__wrapped__(None), tool_catalog()
    if claim['attribute_roles'] != answer['attribute_roles']:
        raise ValueError('static catalog role definitions disagree')
    return claim, answer


def _fragments(path, value, budget=None):
    budget = [0] if budget is None else budget
    budget[0] += 1
    if budget[0] > 4096 or len(path) > 32:
        raise ValueError('static catalog definition traversal limit')
    row = {'path': path, 'value': value}
    encoded = _encoded(row)
    if len(encoded) > 1048576:
        raise ValueError('static catalog definition byte limit')
    if len(encoded) <= MAX_ITEM_BYTES:
        return [row]
    if isinstance(value, (dict, list)) and value:
        children = value.items() if isinstance(value, dict) else enumerate(value)
        return [row for key, child in children for row in _fragments(path + [key], child, budget)]
    # Split an oversize value into exact JSON fragments; join them in order, then decode.
    literal = _encoded(value).decode('ascii')
    chunks = [literal[i:i + 1024] for i in range(0, len(literal), 1024)]
    return [{'path': path, 'encoding': 'json-ascii-fragment', 'offset': index * 1024,
             'length': len(chunk), 'total_length': len(literal), 'fragment': chunk}
            for index, chunk in enumerate(chunks)]


def _rows(claim, answer):
    sections = {
        'claim_forms': [row for name, definition in claim['forms'].items()
                        for row in _fragments(['forms', name], definition)],
        'answer_fields': [row for name, fields in answer['forms'].items() for field, definition in fields.items()
                          for row in _fragments(['forms', name, field], definition)],
        'attribute_roles': [row for name, definition in answer['attribute_roles'].items()
                            for row in _fragments(['attribute_roles', name], definition)],
        'metadata': [row for source, catalog in (('claim_catalog', claim), ('answer_catalog', answer))
                     for name, definition in catalog.items() if name not in ('forms', 'attribute_roles')
                     for row in _fragments([source, name], definition)]}
    if sum(map(len, sections.values())) > 20000:
        raise ValueError('static catalog row limit')
    return sections


def forms_page(*, section=None, offset=None, page_size=None, state_token=None, form=None, role=None):
    if section is not None and section not in SECTIONS:
        raise ValueError('unsupported static catalog section')
    if type(offset) not in (int, type(None)) or offset is not None and offset < 0:
        raise ValueError('catalog offset must be a nonnegative integer')
    if type(page_size) not in (int, type(None)) or page_size is not None and not 1 <= page_size <= MAX_PAGE_SIZE:
        raise ValueError('catalog page_size must be an integer from 1 to 100')
    for name, value in (('form', form), ('role', role)):
        if value is not None and (type(value) is not str or not 1 <= len(value) <= 128):
            raise ValueError('catalog ' + name + ' must be a nonempty name')
    if form is not None and role is not None:
        raise ValueError('catalog form and role filters cannot be combined')
    if state_token is not None and (type(state_token) is not str or len(state_token) != 64
                                    or any(char not in '0123456789abcdef' for char in state_token)):
        raise ValueError('catalog state_token must be a SHA-256 token')
    offset, page_size = offset or 0, page_size or DEFAULT_PAGE_SIZE
    if offset and state_token is None:
        raise ValueError('catalog continuation requires state_token')
    section = section or ('attribute_roles' if role is not None else 'claim_forms')
    if form is not None and section not in ('claim_forms', 'answer_fields') or role is not None and section != 'attribute_roles':
        raise ValueError('catalog name filter does not apply to this section')
    claim, answer = _catalogs()
    if form is not None and form not in (claim['forms'] if section == 'claim_forms' else answer['forms']):
        raise ValueError('catalog form name not found')
    if role is not None and role not in answer['attribute_roles']:
        raise ValueError('catalog role name not found')
    sections = _rows(claim, answer)
    token = hashlib.sha256(_encoded({'version': VERSION, 'claim': claim, 'answer': answer,
                                     'section': section, 'form': form, 'role': role})).hexdigest()
    if state_token is not None and state_token != token:
        raise ValueError('catalog state_token is stale or belongs to another section/name filter; restart at offset 0')
    rows = sections[section]
    if form is not None:
        rows = [row for row in rows if row['path'][1] == form]
    if role is not None:
        rows = [row for row in rows if row['path'][1] == role]
    if offset > len(rows):
        raise ValueError('catalog offset exceeds section total')
    names = {'claim_forms': list(claim['forms']), 'answer_fields': list(answer['forms'])}
    index = {key: value if len(_encoded(value)) <= 8192 else {
        'total_names': len(value), 'discovery': 'Page ' + key + ' to retrieve every exact name.'}
        for key, value in names.items()}
    page = {'offset': offset, 'page_size': page_size, 'returned': 0, 'total': len(rows),
            'next_offset': None, 'items': []}
    result = {'view': 'static_form_catalog_page', 'schema_version': VERSION, 'section': section,
              'form': form, 'role': role, 'state_token': token,
              'sections': list(SECTIONS), 'counts': {name: len(value) for name, value in sections.items()},
              'form_names': index, 'attribute_role_count': len(answer['attribute_roles']), 'page': page,
              'continuation': 'Repeat section/form/role/page_size and state_token with page.next_offset until null. Named form lookup: claim_forms for signatures, answer_fields for selectors. Named role lookup: attribute_roles with role.',
              'references': "allowed_semantic_types_ref '#/attribute_roles' refers to the complete attribute_roles section. Every exact role definition is paged there once.",
              'fragment_policy': 'Rows contain exact path/value. For json-ascii-fragment rows at one path, join fragment strings by offset and JSON-decode; total_length is the complete encoded literal length.',
              'scope': 'Static public catalog only; no evidence availability, certificate, relevance or completeness is established.'}
    for row in rows[offset:offset + page_size]:
        page['items'].append(deepcopy(row))
        page['returned'] = len(page['items'])
        next_offset = offset + page['returned']
        page['next_offset'] = next_offset if next_offset < len(rows) else None
        if len(json.dumps(result, ensure_ascii=True, allow_nan=False).encode('utf-8')) > MAX_RESPONSE_BYTES:
            page['items'].pop()
            page['returned'] = len(page['items'])
            next_offset = offset + page['returned']
            page['next_offset'] = next_offset if next_offset < len(rows) else None
            break
    if (offset < len(rows) and not page['returned']) or len(json.dumps(result, ensure_ascii=True, allow_nan=False).encode('utf-8')) > MAX_RESPONSE_BYTES:
        raise ValueError('static catalog entry/envelope exceeds response byte bound')
    return result
