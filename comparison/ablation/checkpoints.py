"""Durable investigator-authored binding documents; no certification or repair."""
from __future__ import annotations
import hashlib
import json
import os
import time
import uuid

from comparison.ablation.bindings import extract_bindings

PROTOCOL = 'claim-bindings-v3'
FILE = 'binding-checkpoint.json'


def public_preflight(public):
    """Reject missing/invalid declarations before any investigator session exists."""
    from agent.answer_requirements import inspect
    from agent.answer_projection import catalog
    forms = catalog()['forms']
    rows = [{'question_id': question['id'], **row}
            for question in public['questions']
            for row in inspect(question['answer_schema'], forms, require_claim_requirements=True)['requirements']]
    invalid = [row for row in rows if row['status'] in ('missing_annotation', 'invalid')]
    if invalid:
        diagnostics = [{key: row[key] for key in ('question_id', 'path', 'status', 'reason') if key in row}
                       for row in invalid[:20]]
        raise ValueError('v3 public claim contract is not ready: ' + json.dumps(
            {'invalid_count': len(invalid), 'diagnostics': diagnostics}, ensure_ascii=True)[:12000])
    unsupported = [row for row in rows if row['status'] == 'no_catalog_support']
    return {'status': 'ready', 'declared_fields': len(rows),
            'supported_fields': len(rows)-len(unsupported), 'unsupported_fields': len(unsupported),
            'evidence_needs': [{key: row[key] for key in ('question_id', 'path', 'status', 'requirement') if key in row}
                               for row in unsupported[:100]],
            'truncated': len(unsupported) > 100,
            'scope': 'Public declarations only. Unsupported declared roles remain unknown until an approved form and evidence exist.'}


def deadline(session):
    value = session.get('deadline_unix')
    if type(value) not in (int, float) or not __import__('math').isfinite(value):
        raise ValueError('v3 requires a finite explicit session deadline')
    if time.time() >= value:
        raise ValueError('investigator session deadline has passed')


def validate(document, public):
    raw = json.dumps(document, ensure_ascii=False, allow_nan=False).encode()
    exact, _ = extract_bindings(b'```json\n' + raw + b'\n```\n', public)
    return exact


def candidate_bytes(directory, arm):
    from comparison.ablation.runtime import _read
    path = directory / ('candidates.jsonl' if arm == 'A' else 'proposals.jsonl')
    if path.is_symlink():
        raise ValueError('candidate log must not be a symlink')
    raw = _read(path) if path.exists() else b''
    if raw and not raw.endswith(b'\n'):
        raise ValueError('incomplete candidate log')
    return raw


def preview(directory, session, bench, document):
    from agent.case import read_question_profile
    from agent.answer_projection import project_answers
    from comparison.ablation.runtime import _json
    public = read_question_profile(directory / 'questions.json')
    document = validate(document, public)
    raw = candidate_bytes(directory, session['arm'])
    candidates = [_json(line) for line in raw.splitlines()]
    from comparison.ablation.bindings import resolve_hashes
    resolved, _ = resolve_hashes(document['bindings'], candidates)
    result = project_answers(public, candidates, resolved, bench.source,
                             require_claim_requirements=True, authority='unchecked')
    # Return bounded public diagnostics, never the projected answer population.
    from agent.answer_requirements import inspect
    from agent.answer_projection import catalog
    requirements = [{'question_id': q['id'], **row}
                    for q in public['questions']
                    for row in inspect(q['answer_schema'], catalog()['forms'], require_claim_requirements=True)['requirements']]
    diagnostics = result['unsupported'] + result['conflicts']
    diagnostics += [row for row in requirements if row['status'] not in ('catalog_support',)]
    return {'status': 'uncertified', 'diagnostics': [{'diagnostic': json.dumps(row, ensure_ascii=True)[:2000]} for row in diagnostics[:100]],
            'diagnostic_count': len(diagnostics), 'truncated': len(diagnostics) > 100,
            'coverage': {'questions': len(public['questions']),
                         'bindings': len(document['bindings']),
                         'unanswered': len(document['unanswered'])},
            'scope': 'Exact claim-field and public schema compatibility only; no proof, semantic support, accuracy or completeness check.'}


def checkpoint(directory, session, document):
    from agent.case import read_question_profile
    from comparison.ablation.runtime import _encoded, _binding, _now
    deadline(session)
    public = read_question_profile(directory / 'questions.json')
    document = validate(document, public)
    raw = candidate_bytes(directory, session['arm'])
    payload = {'schema_version': 1, 'protocol': PROTOCOL, 'document': document,
               'authored_at': _now(), 'authored_unix': time.time(),
               'author': 'investigator_tool_document',
               'session': _binding(directory / 'session.json'),
               'document_sha256': hashlib.sha256(_encoded(document)).hexdigest(),
               'candidate_population': {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}}
    encoded = _encoded(payload)
    temp = directory / ('.checkpoint-' + uuid.uuid4().hex)
    prior = directory / ('.checkpoint-prior-' + uuid.uuid4().hex)
    target = directory / FILE
    existed = target.exists()
    if existed:
        os.link(target, prior, follow_symlinks=False)
    try:
        with temp.open('xb') as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        deadline(session)
        os.replace(temp, target)
        try:
            deadline(session)
        except BaseException:
            if existed:
                os.replace(prior, target)
            else:
                target.unlink()
            raise
    finally:
        temp.unlink(missing_ok=True)
        prior.unlink(missing_ok=True)
    return {'status': 'saved', 'checkpoint_sha256': hashlib.sha256(encoded).hexdigest(),
            'document_sha256': payload['document_sha256'], 'authored_at': payload['authored_at'],
            'candidate_population': payload['candidate_population']}


def load(directory, session):
    from comparison.ablation.runtime import _read, _json, _binding, _encoded
    from agent.case import read_question_profile
    payload = _json(_read(directory / FILE))
    if (payload.get('protocol') != PROTOCOL or payload.get('author') != 'investigator_tool_document'
            or payload.get('session') != _binding(directory / 'session.json')
            or type(payload.get('authored_unix')) not in (int, float)
            or not payload['authored_unix'] < session['deadline_unix']):
        raise ValueError('invalid checkpoint receipt or deadline')
    document = validate(payload['document'], read_question_profile(directory / 'questions.json'))
    if hashlib.sha256(_encoded(document)).hexdigest() != payload['document_sha256']:
        raise ValueError('checkpoint document hash mismatch')
    raw = candidate_bytes(directory, session['arm'])
    population = payload['candidate_population']
    size = population['bytes']
    if type(size) is not int or size < 0 or size > len(raw) or hashlib.sha256(raw[:size]).hexdigest() != population['sha256']:
        raise ValueError('checkpoint candidate population changed')
    return document
