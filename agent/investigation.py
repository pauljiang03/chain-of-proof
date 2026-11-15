"""Persistent public-question work notes, separate from proof and completeness."""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import tempfile
import uuid

from agent.case import CaseProfile, validate_zone
from checker.check import valid_finding_id

STATUSES = frozenset({'not_started', 'in_progress', 'blocked', 'reviewed'})
MAX_QUESTIONS, MAX_ITEMS, MAX_HISTORY, MAX_BYTES = 500, 512, 2000, 16 * 1024 * 1024
DISCLAIMER = ('Work status, searches, unresolved fields and next actions are agent-reported notes, '
              'not certified facts or proof of investigation completeness. Reviewed does not mean answered, '
              'accurate or complete. Finding references require current-run certificates; independent replay is separate.')


def _utc():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def _text(value, name, limit=4000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f'{name} must be a nonempty string of at most {limit} characters')
    return value


def _strings(value, name, limit=1000):
    if not isinstance(value, (list, tuple)) or len(value) > MAX_ITEMS:
        raise ValueError(f'{name} must be a list of at most {MAX_ITEMS} strings')
    return list(dict.fromkeys(_text(v, name, limit) for v in value))


def _read_json(path):
    path = Path(path)
    if path.is_symlink():
        raise ValueError(f'{path.name} cannot be a symlink')
    if path.stat().st_size > MAX_BYTES:
        raise ValueError(f'{path.name} exceeds the supported file size')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    def constant(_):
        raise ValueError('non-finite JSON number')
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=pairs, parse_constant=constant)


def atomic_json(path, value):
    """Replace one bounded JSON artifact atomically; never follow an artifact symlink."""
    path = Path(path)
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError('JSON artifact or run directory cannot be a symlink')
    encoded = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
    if len(encoded) > MAX_BYTES:
        raise ValueError('JSON artifact exceeds the supported file size')
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        if path.is_symlink():
            raise ValueError('JSON artifact cannot be a symlink')
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def question_spec(profile, public_questions=None):
    """Normalize public CaseProfile/string questions or the existing public v2 shape."""
    context = profile.public_dict() if isinstance(profile, CaseProfile) else deepcopy(profile)
    if not isinstance(context, dict):
        raise ValueError('profile must be public case context')
    public = public_questions
    if context.get('schema_version') == 2:
        if public is not None and public != context:
            raise ValueError('two different public question profiles were supplied')
        public, context = context, {}
    if set(context) - {'name', 'brief', 'questions', 'time_zone', 'case_id'}:
        raise ValueError('case profile contains unsupported/private fields')
    if public is not None:
        allowed = {'schema_version', 'case_id', 'title', 'time_zone', 'instructions', 'questions', 'contract_revision'}
        if not isinstance(public, dict) or public.get('schema_version') != 2 or set(public) - allowed:
            raise ValueError('public questions must use the public schema-v2 contract')
        case_id = _text(public.get('case_id'), 'case_id', 200)
        if context.get('case_id') not in (None, case_id):
            raise ValueError('public question case_id conflicts with the case profile')
        context_zone, public_zone = validate_zone(context.get('time_zone')), validate_zone(public.get('time_zone'))
        if context_zone and public_zone and context_zone != public_zone:
            raise ValueError('public question timezone conflicts with the case profile')
        source = public.get('questions')
        if not isinstance(source, list):
            raise ValueError('public questions must be a list')
        questions = []
        for row in source:
            if not isinstance(row, dict) or set(row) - {'id', 'prompt', 'answer_schema', 'match'}:
                raise ValueError('public question contains unsupported/private fields')
            if not isinstance(row.get('answer_schema'), dict):
                raise ValueError('public question answer_schema must be an object')
            question = {'id': _text(row.get('id'), 'question id', 128),
                        'prompt': _text(row.get('prompt'), 'question prompt'),
                        'answer_schema': deepcopy(row['answer_schema'])}
            questions.append(question)
        name = context.get('name') or public.get('title') or case_id
        zone = public_zone or context_zone
    else:
        case_id = _text(context['case_id'], 'case_id', 200) if context.get('case_id') is not None else None
        source = context.get('questions')
        if not isinstance(source, (list, tuple)):
            raise ValueError('profile questions must be a list of public strings')
        questions = [{'id': f'Q{i}', 'prompt': _text(prompt, 'question prompt')}
                     for i, prompt in enumerate(source, 1)]
        name, zone = context.get('name'), validate_zone(context.get('time_zone'))
    if not 1 <= len(questions) <= MAX_QUESTIONS:
        raise ValueError(f'provide between 1 and {MAX_QUESTIONS} public questions')
    if len({row['id'] for row in questions}) != len(questions):
        raise ValueError('public question IDs must be unique')
    result = {'case_id': case_id, 'name': _text(name, 'case name', 500), 'time_zone': zone, 'questions': questions}
    if len(json.dumps(result, allow_nan=False).encode()) > MAX_BYTES // 4:
        raise ValueError('public question profile exceeds the supported size')
    return result


def current_certificates(run_dir, finding_ids):
    """Check same-run recorded status and matching certificate/proposal fields; no replay."""
    directory = Path(run_dir)
    ids = _strings(finding_ids, 'finding_ids', 32)
    if any(not valid_finding_id(fid) for fid in ids):
        raise ValueError('finding_ids must name current-run certificates')
    path = directory / 'proposals.jsonl'
    if path.is_symlink():
        raise ValueError('proposal log cannot be a symlink')
    proposals = {}
    if path.is_file():
        with path.open(encoding='utf-8') as stream:
            for line in stream:
                if line.strip():
                    row = json.loads(line)
                    if isinstance(row, dict) and row.get('finding_id') in ids:
                        fid = row['finding_id']
                        if fid in proposals and proposals[fid] != row:
                            raise ValueError('conflicting proposal definitions')
                        proposals[fid] = row
    result = {}
    for fid in ids:
        proposal = proposals.get(fid, {})
        cert_path = directory / (fid + '.json')
        if proposal.get('status') != 'verified' or not cert_path.is_file():
            raise ValueError(f'{fid} is not a verified finding of this run')
        cert = _read_json(cert_path)
        if not isinstance(cert, dict) or cert.get('status') != 'verified' or cert.get('finding_id') != fid:
            raise ValueError(f'{fid} has no matching verified certificate')
        for field in ('claim', 'english', 'cited_facts', 'rules', 'strength', 'trust_tier', 'axioms'):
            if field not in cert or cert[field] != proposal.get(field):
                raise ValueError(f'{fid} certificate differs from its recorded proposal')
        if not isinstance(cert['english'], str) or not cert['english']:
            raise ValueError(f'{fid} has no certified sentence')
        result[fid] = cert
    return result


class Investigation:
    def __init__(self, run_dir):
        self.directory = Path(run_dir)
        self.path = self.directory / 'investigation.json'

    @contextmanager
    def _locked(self):
        if self.directory.is_symlink():
            raise ValueError('run directory cannot be a symlink')
        self.directory.mkdir(parents=True, exist_ok=True)
        lock = self.directory / '.investigation.lock'
        descriptor = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    def _evidence(self):
        path = self.directory / 'run-manifest.json'
        if not path.exists() and not path.is_symlink():
            return None
        manifest = _read_json(path)
        value = manifest.get('inputs', {}).get('facts', {}).get('sha256')
        if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value):
            raise ValueError('run manifest lacks a valid evidence SHA-256')
        return value

    def _load(self):
        state = _read_json(self.path)
        if not isinstance(state, dict) or state.get('schema_version') != 1:
            raise ValueError('unsupported investigation state')
        revision, history = state.get('revision'), state.get('history')
        if (type(revision) is not int or not isinstance(history, list) or revision != len(history)
                or not 1 <= revision <= MAX_HISTORY
                or any(not isinstance(event, dict) or event.get('sequence') != i
                       for i, event in enumerate(history, 1))):
            raise ValueError('investigation history is not a contiguous revision sequence')
        questions = state.get('questions')
        if (not isinstance(questions, list) or not 1 <= len(questions) <= MAX_QUESTIONS
                or any(not isinstance(q, dict) for q in questions)):
            raise ValueError('invalid investigation questions')
        ids = []
        for question in questions:
            ids.append(_text(question.get('id'), 'question id', 128))
            _text(question.get('prompt'), 'question prompt')
            if question.get('work_status') not in STATUSES:
                raise ValueError('invalid question work status')
            for key in ('finding_ids', 'searched', 'unresolved', 'next_actions'):
                _strings(question.get(key), key, 32 if key == 'finding_ids' else 1000)
        if len(ids) != len(set(ids)):
            raise ValueError('duplicate investigation question IDs')
        if state.get('facts_sha256') != self._evidence():
            raise ValueError('evidence changed; initialize a new run with unverified continuation notes')
        return state

    def initialize(self, profile, public_questions=None, *, continuation=None):
        spec = question_spec(profile, public_questions)
        with self._locked():
            if self.path.exists() or self.path.is_symlink():
                state = self._load()
                stored = {key: state[key] for key in ('case_id', 'name', 'time_zone')}
                stored['questions'] = [{k: q[k] for k in ('id', 'prompt', 'answer_schema') if k in q}
                                       for q in state['questions']]
                if stored != spec or continuation is not None:
                    raise ValueError('existing investigation cannot be replaced or reinitialized')
                return deepcopy(state)
            now = _utc()
            state = dict(spec, schema_version=1, run_id=str(uuid.uuid4()), facts_sha256=self._evidence(),
                         revision=1, created_at=now, updated_at=now, disclaimer=DISCLAIMER,
                         history=[{'sequence': 1, 'at': now, 'action': 'initialize'}])
            for question in state['questions']:
                question.update(work_status='not_started', finding_ids=[], searched=[], unresolved=[], next_actions=[])
            if continuation is not None:
                self._carry_notes(state, continuation)
            atomic_json(self.path, state)
            return deepcopy(state)

    def snapshot(self):
        with self._locked():
            if not self.path.exists() and not self.path.is_symlink():
                return {'schema_version': 1, 'status': 'unavailable', 'questions': [],
                        'reason': 'A public question plan has not been initialized.', 'disclaimer': DISCLAIMER}
            return deepcopy(self._load())

    def update(self, question_id, finding_ids=None, searched=None, unresolved=None, next_actions=None, status=None):
        with self._locked():
            state = self._load()
            question = next((q for q in state['questions'] if q['id'] == question_id), None)
            if question is None:
                raise ValueError('question_id must name a public question in this investigation')
            changes = {}
            for name, supplied in (('finding_ids', finding_ids), ('searched', searched),
                                   ('unresolved', unresolved), ('next_actions', next_actions)):
                if supplied is not None:
                    values = _strings(supplied, name, 32 if name == 'finding_ids' else 1000)
                    if name == 'finding_ids':
                        current_certificates(self.directory, values)
                    if name in ('finding_ids', 'searched'):
                        values = _strings(question[name] + values, name, 32 if name == 'finding_ids' else 1000)
                    changes[name] = values
            if status is not None:
                if status not in STATUSES:
                    raise ValueError('status must be one of ' + ', '.join(sorted(STATUSES)))
                changes['work_status'] = status
            if not changes:
                return deepcopy(state)
            if state['revision'] >= MAX_HISTORY:
                raise ValueError('investigation history limit reached; preserve this run and continue in a new run')
            question.update(changes)
            state['revision'] += 1
            state['updated_at'] = _utc()
            state['history'].append({'sequence': state['revision'], 'at': state['updated_at'],
                                     'action': 'update', 'question_id': question_id, 'changes': changes})
            atomic_json(self.path, state)
            return deepcopy(state)

    def continuation(self):
        """Carry work notes only, even when the next run uses the same evidence bytes."""
        state = self.snapshot()
        if state.get('status') == 'unavailable':
            raise ValueError('initialize a public question plan before exporting continuation notes')
        questions = []
        for question in state['questions']:
            prior = question.get('previous_run_notes', {})
            revised = {key for event in state['history'] if event.get('question_id') == question['id']
                       for key in event.get('changes', {})}
            row = {key: question[key] for key in ('id', 'prompt')}
            for key in ('searched', 'unresolved', 'next_actions'):
                previous = prior.get(key, [])
                if key == 'searched':
                    row[key] = _strings(previous + question[key], key)
                else:
                    row[key] = deepcopy(question[key] if key in revised else previous or question[key])
            questions.append(row)
        return {'schema_version': 1, 'kind': 'unverified_continuation', 'case_id': state['case_id'],
                'source_run_id': state['run_id'], 'source_facts_sha256': state['facts_sha256'],
                'questions': questions,
                'disclaimer': 'Previous-run work notes only, unverified. No finding IDs or proof status carry over. '
                              'Re-query the current evidence and certify any claims in the new run.'}

    @staticmethod
    def _carry_notes(state, continuation):
        if (not isinstance(continuation, dict) or continuation.get('schema_version') != 1
                or continuation.get('kind') != 'unverified_continuation'
                or continuation.get('case_id') != state['case_id']):
            raise ValueError('continuation must contain unverified notes for the same public case')
        old = continuation.get('questions')
        if (not isinstance(old, list) or len(old) > len(state['questions'])
                or any(not isinstance(row, dict) for row in old)):
            raise ValueError('continuation must preserve all public questions')
        current = {question['id']: question for question in state['questions']}
        seen = set()
        for previous in old:
            old_id = previous.get('id')
            if not isinstance(old_id, str) or old_id in seen or old_id not in current:
                raise ValueError('continuation must preserve unique prior public question IDs')
            seen.add(old_id)
            question = current[old_id]
            if previous.get('prompt') != question['prompt']:
                raise ValueError('continuation question differs from the public profile')
            # Never copy supplied status, finding IDs, or previous history, even if inserted by a caller.
            question['previous_run_notes'] = {key: _strings(previous.get(key, []), key)
                                               for key in ('searched', 'unresolved', 'next_actions')}
            question['previous_run_notes']['status'] = 'unverified'
        state['continuation'] = {'source_run_id': continuation.get('source_run_id'),
                                 'source_facts_sha256': continuation.get('source_facts_sha256'),
                                 'status': 'unverified_notes_only'}
