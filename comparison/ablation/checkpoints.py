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


class SessionDeadlineExceeded(ValueError):
    """The investigator budget expired; this is not a proof verdict."""


def _work_state(directory):
    from agent.investigation import Investigation
    try:
        return Investigation(directory).snapshot()
    except (ValueError, OSError, KeyError, TypeError):
        return None


def public_preflight(public):
    """Reject missing/invalid declarations before any investigator session exists."""
    from agent.answer_requirements import inspect
    from agent.answer_projection import catalog
    from agent.answer_references import validate_public
    references = validate_public(public)
    if references['errors']:
        raise ValueError('v3 public answer references are not ready: ' + json.dumps(references['errors'][:20], ensure_ascii=True)[:12000])
    forms = catalog()['forms']
    rows, scopes = [], []
    for question in public['questions']:
        inspected = inspect(question['answer_schema'], forms, require_claim_requirements=True, require_evidence_scope=True)
        rows.extend({'question_id': question['id'], **row} for row in inspected['requirements'])
        scopes.extend({'question_id': question['id'], **row} for row in inspected['scope_requirements'])
    invalid = [row for row in rows if row['status'] in ('missing_annotation', 'invalid')]
    if invalid:
        diagnostics = [{key: row[key] for key in ('question_id', 'path', 'status', 'reason') if key in row}
                       for row in invalid[:20]]
        raise ValueError('v3 public claim contract is not ready: ' + json.dumps(
            {'invalid_count': len(invalid), 'diagnostics': diagnostics}, ensure_ascii=True)[:12000])
    unsupported = [row for row in rows if row['status'] == 'no_catalog_support']
    unavailable = [row for row in scopes if row['status'] == 'unavailable']
    needs = unsupported + unavailable
    return {'status': 'ready', 'declared_fields': len(rows),
            'supported_fields': len(rows)-len(unsupported), 'unsupported_fields': len(unsupported),
            'evidence_needs': [{key: row[key] for key in ('question_id', 'path', 'status', 'requirement') if key in row}
                               for row in needs[:100]],
            'scope_requirements': scopes[:100], 'unavailable_scopes': len(unavailable),
            'reference_requirements': references['reference_requirements'][:100],
            'truncated': len(needs) > 100 or len(scopes) > 100,
            'scope': 'Public declarations only. Unsupported declared roles and unavailable source scopes remain explicit gaps; declaring a gap does not enable its bindings.'}


def deadline(session):
    value = session.get('deadline_unix')
    if type(value) not in (int, float) or not __import__('math').isfinite(value):
        raise ValueError('v3 requires a finite explicit session deadline')
    if time.time() >= value:
        raise SessionDeadlineExceeded('investigator session deadline has passed')


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


def completion_status(directory, session, source):
    """Use only the last authenticated checkpoint population, never late claims."""
    from agent.case import read_question_profile
    from agent.answer_projection import project_answers
    from agent.completion_diagnostics import completion_diagnostics, LIMITATION
    from agent.inventory_pages import inventory_progress
    from comparison.ablation.bindings import resolve_hashes
    from comparison.ablation.runtime import _read, _json
    current = None
    try:
        raw = candidate_bytes(directory, session['arm'])
        current = [_json(line) for line in raw.splitlines()]
        document, receipt = load_checkpoint(directory, session)
        population = raw[:receipt['candidate_population']['bytes']]
        # load authenticated these prefix bytes. Recheck after its read rather
        # than interpreting newly appended candidates as checkpoint dependencies.
        if (len(population) != receipt['candidate_population']['bytes']
                or hashlib.sha256(population).hexdigest() != receipt['candidate_population']['sha256']):
            raise ValueError('checkpoint population changed during diagnostics')
        saved = [_json(line) for line in population.splitlines()]
        public = read_question_profile(directory / 'questions.json')
        resolved, _ = resolve_hashes(document['bindings'], saved)
        projection = project_answers(public, saved, resolved, source, require_claim_requirements=True,
            require_evidence_scope=True, evidence_facts_sha256=session['facts']['sha256'], authority='unchecked')
        try:
            inventory = inventory_progress(directory, evidence_sha256=session['facts']['sha256'])
        except (ValueError, OSError, TypeError):
            inventory = {'status': 'invalid', 'traversals': []}
        return completion_diagnostics(public, document, projection, current, inventory,
            work_state=_work_state(directory),
            checkpoint={'status': 'saved', 'authored_at': receipt['authored_at'],
                'saved_candidates': len(saved), 'candidates_since_checkpoint': len(current)-len(saved)})
    except (ValueError, OSError, KeyError, TypeError, RecursionError) as error:
        # Missing/invalid documents supply no answer state. Counts of returned
        # work remain inspectable without constructing an unanswered submission.
        try:
            inventory = inventory_progress(directory, evidence_sha256=session['facts']['sha256'])
            returned = sum(row['rows_returned'] for row in inventory['traversals'])
            pending = sum(not row['exhausted'] for row in inventory['traversals'])
            inventory_status = inventory['status']
        except (ValueError, OSError, KeyError, TypeError):
            returned = pending = None
            inventory_status = 'invalid'
        return {'status': 'unavailable', 'checkpoint': {'status': 'missing_or_invalid'},
                'reason': type(error).__name__, 'detail': str(error)[:500],
                'counts': {'current_candidates': len(current) if current is not None else None,
                           'inventory_rows_returned': returned, 'pending_inventory': pending},
                'inventory_status': inventory_status,
                'limitation': LIMITATION, 'answers_inferred': False}


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
                             require_claim_requirements=True, require_evidence_scope=True,
                             evidence_facts_sha256=session['facts']['sha256'], authority='unchecked')
    # Return bounded public diagnostics, never the projected answer population.
    from agent.answer_requirements import inspect
    from agent.answer_projection import catalog
    forms = catalog()['forms']
    requirements = [{'question_id': q['id'], **row}
                    for q in public['questions']
                    for row in inspect(q['answer_schema'], forms, require_claim_requirements=True, require_evidence_scope=True)['requirements']]
    diagnostics = result['unsupported'] + result['conflicts']
    diagnostics += [row for row in requirements if row['status'] not in ('catalog_support',)]
    from agent.completion_diagnostics import completion_diagnostics
    from agent.inventory_pages import inventory_progress
    try:
        inventory = inventory_progress(directory, evidence_sha256=session['facts']['sha256'])
    except (ValueError, OSError, TypeError):
        inventory = {'status': 'invalid', 'traversals': []}
    completion = completion_diagnostics(public, document, result, candidates, inventory,
        work_state=_work_state(directory),
        checkpoint={'status': 'preview_only', 'persisted': False})
    return {'completion': completion, 'status': 'uncertified', 'diagnostics': [{'diagnostic': json.dumps(row, ensure_ascii=True)[:2000]} for row in diagnostics[:100]],
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
    removed_count = 0
    prior_status = 'absent'
    if (directory / FILE).exists():
        try:
            prior_document = load(directory, session)
            current_rows = {json.dumps(row, sort_keys=True, allow_nan=False) for row in document['bindings']}
            removed_count = sum(json.dumps(row, sort_keys=True, allow_nan=False) not in current_rows
                                for row in prior_document['bindings'])
            prior_status = 'valid'
        except (ValueError, OSError, KeyError, TypeError):
            prior_status = 'invalid'
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
    return {'status': 'saved', 'previous_checkpoint': prior_status,
            'removed_authored_bindings': removed_count,
            'replacement_note': 'Full investigator-authored replacement; removed bindings were not repaired or restored.',
            'checkpoint_sha256': hashlib.sha256(encoded).hexdigest(),
            'document_sha256': payload['document_sha256'], 'authored_at': payload['authored_at'],
            'candidate_population': payload['candidate_population']}


def load_checkpoint(directory, session):
    """Return document and receipt validated from one immutable read of bytes."""
    from comparison.ablation.runtime import _read, _json, _binding, _encoded
    from agent.case import read_question_profile
    raw_payload = _read(directory / FILE)
    payload = _json(raw_payload)
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
    return document, dict(payload, _checkpoint_binding={
        'sha256': hashlib.sha256(raw_payload).hexdigest(), 'bytes': len(raw_payload)})


def load(directory, session):
    """Compatibility document-only accessor over the same validated receipt."""
    return load_checkpoint(directory, session)[0]
