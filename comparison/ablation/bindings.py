"""Strict final binding-document transport and exact missing-hash resolution.

No prose inference, evidence access, projection, scoring or answer repair occurs.
A binding naming a public question accounts for an attempted binding even when
its selectors are invalid. Its semantic support is left to the shared projector.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
import re

from agent.answer_projection import claim_digest

MAX_BYTES = 16 * 1024 * 1024
MAX_BINDINGS = 20000
MAX_CANDIDATES = 100000
MAX_QUESTIONS = 500
MAX_DEPTH = 64
MAX_NODES = 1000000
_OPEN = re.compile(rb'^```json[ \t]*\r?\n', re.MULTILINE)
_BLOCK = re.compile(rb'^```json[ \t]*\r?\n(.*?)^```[ \t]*(?:\r?\n|\Z)', re.MULTILINE | re.DOTALL)


def _bounded_json(value):
    """Check finite exact JSON types and structural bounds before copying/hashing."""
    pending, count = [(value, 0)], 0
    while pending:
        current, depth = pending.pop()
        count += 1
        if count > MAX_NODES or depth > MAX_DEPTH:
            raise ValueError('binding inputs exceed the node or depth limit')
        if current is None or type(current) in (str, bool, int):
            continue
        if type(current) is float and math.isfinite(current):
            continue
        if type(current) is list:
            children = current
        elif type(current) is dict and all(type(key) is str for key in current):
            children = current.values()
        else:
            raise ValueError('binding inputs must be finite JSON values')
        if count + len(pending) + len(current) > MAX_NODES:
            raise ValueError('binding inputs exceed the node limit')
        pending.extend((child, depth + 1) for child in children)
    try:
        encoded = json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(',', ':')).encode()
    except (ValueError, OverflowError, RecursionError) as error:
        raise ValueError('binding inputs cannot be encoded as bounded JSON') from error
    if len(encoded) > MAX_BYTES:
        raise ValueError('binding inputs exceed the byte limit')


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def _constant(value):
    raise ValueError('non-finite JSON number')


def _id(value, maximum=128):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= maximum


def _public(public):
    if (not isinstance(public, dict) or not _id(public.get('case_id'), 200)
            or not isinstance(public.get('questions'), list)
            or not 1 <= len(public['questions']) <= MAX_QUESTIONS):
        raise ValueError('invalid public question contract')
    ids = []
    for row in public['questions']:
        if not isinstance(row, dict) or not _id(row.get('id')) or row['id'] in ids:
            raise ValueError('public question IDs must be unique bounded strings')
        ids.append(row['id'])
    return set(ids)


def extract_bindings(summary_bytes, public):
    """Return the strict document and exact bytes inside its sole JSON fence.

    Every public question must have a binding naming it or one explicit unanswered
    entry. Unknown question IDs in bindings survive unchanged but cannot account
    for a public question. Invalid selectors/values are preserved for projection.
    """
    ids = _public(public)
    if not isinstance(summary_bytes, bytes) or len(summary_bytes) > MAX_BYTES:
        raise ValueError('summary must be bounded UTF-8 bytes')
    try:
        summary_bytes.decode('utf-8')
    except UnicodeError as error:
        raise ValueError('summary must be UTF-8') from error
    matches = list(_BLOCK.finditer(summary_bytes))
    if len(matches) != 1 or len(_OPEN.findall(summary_bytes)) != 1:
        raise ValueError('summary must have exactly one fenced json block')
    raw = matches[0].group(1)
    try:
        document = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs, parse_constant=_constant)
    except (UnicodeError, ValueError, RecursionError) as error:
        raise ValueError('binding block must be strict finite JSON with unique keys') from error
    _bounded_json(document)
    if (not isinstance(document, dict) or set(document) != {'schema_version', 'case_id', 'bindings', 'unanswered'}
            or type(document['schema_version']) is not int or document['schema_version'] != 1
            or document['case_id'] != public['case_id']
            or not isinstance(document['bindings'], list) or len(document['bindings']) > MAX_BINDINGS
            or not isinstance(document['unanswered'], list) or len(document['unanswered']) > MAX_QUESTIONS):
        raise ValueError('invalid binding document shape or case')
    named = {binding['question_id'] for binding in document['bindings']
             if isinstance(binding, dict) and isinstance(binding.get('question_id'), str)
             and binding['question_id'] in ids}
    unanswered = set()
    for row in document['unanswered']:
        if (not isinstance(row, dict) or set(row) != {'question_id', 'reason'}
                or not _id(row.get('question_id')) or row['question_id'] not in ids
                or row['question_id'] in unanswered or not _id(row.get('reason'), 4000)):
            raise ValueError('unanswered entries need unique public IDs and bounded nonempty reasons')
        unanswered.add(row['question_id'])
    if named & unanswered:
        raise ValueError('a question cannot have both bindings and an unanswered entry')
    if named | unanswered != ids:
        raise ValueError('every public question needs a binding or an unanswered entry')
    return document, raw


def resolve_hashes(bindings, candidates):
    """Fill absent hash keys only; return copied bindings and separate provenance.

    Candidate logs must contain unique, unambiguous IDs, even for identical rows.
    Missing candidates and invalid bindings remain unresolved. Provided hashes,
    including wrong/null values, are never replaced; no other binding field moves.
    """
    if not isinstance(bindings, list) or len(bindings) > MAX_BINDINGS:
        raise ValueError('bindings must be a bounded list')
    if not isinstance(candidates, list) or len(candidates) > MAX_CANDIDATES:
        raise ValueError('candidates must be a bounded list')
    _bounded_json(bindings)
    _bounded_json(candidates)
    indexed = {}
    for candidate in candidates:
        if not isinstance(candidate, dict):
            raise ValueError('candidate must be an object')
        cid = candidate.get('candidate_id', candidate.get('finding_id'))
        if (not _id(cid) or cid in indexed or 'claim' not in candidate
                or candidate.get('candidate_id', cid) != candidate.get('finding_id', cid)):
            raise ValueError('candidate IDs must be unique and unambiguous with exact claims')
        indexed[cid] = candidate['claim']
    resolved, provenance = deepcopy(bindings), []
    for index, binding in enumerate(resolved):
        if not isinstance(binding, dict) or 'claim_sha256' in binding:
            continue
        cid = binding.get('candidate_id')
        if not isinstance(cid, str) or cid not in indexed:
            continue
        digest = claim_digest(indexed[cid])
        binding['claim_sha256'] = digest
        provenance.append({'binding_index': index, 'candidate_id': cid, 'claim_sha256': digest,
                           'hash_source': 'exact_candidate_claim'})
    return resolved, provenance
