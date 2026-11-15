"""Bounded record rendering and snapshot inventory traversal helpers.

Clipping and traversal measure returned extracted records, never forensic completeness.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import stat
from contextlib import contextmanager
from pathlib import Path
import uuid


def render_rows(columns, rows, cell_limit):
    """Render bounded rows with explicit locations of every clipped string cell."""
    clipped, rendered = [], []
    for row_index, row in enumerate(rows):
        values = []
        for column_index, value in enumerate(row):
            if isinstance(value, str) and len(value) > cell_limit:
                clipped.append({"row_index": row_index, "column_index": column_index,
                                "column": columns[column_index], "original_chars": len(value)})
                value = value[:cell_limit] + "…"
            values.append(value)
        rendered.append(values)
    return {"columns": list(columns), "rows": rendered,
            "cells_truncated": bool(clipped), "cell_truncations": clipped}


LIMITATION = ('Traversal covers only the exact predicate in this extracted snapshot, in record-ID order. '
              'Returned rows and exhaustion do not prove inspection, question completeness, or original-evidence completeness.')
MAX_BYTES = 256 * 1024
MAX_TRAVERSALS = 128
MAX_PAGES = 10000


def _run(run_dir):
    path = Path(run_dir)
    if path.is_symlink() or not path.is_dir():
        raise ValueError('inventory run directory must be a real directory, not a symlink')
    return path


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('duplicate inventory JSON key')
        result[key] = value
    return result


def _constant(value):
    raise ValueError('nonfinite inventory JSON value')


def _digest(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def _request_key(request):
    return hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()


def _read(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    if not stat.S_ISREG(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise ValueError('inventory progress must be a regular file')
    with os.fdopen(descriptor, 'rb') as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('inventory progress exceeds its size bound')
    state = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_constant)
    if (not isinstance(state, dict) or set(state) != {'schema_version', 'evidence_sha256', 'traversals'}
            or type(state['schema_version']) is not int or state['schema_version'] != 1
            or not _digest(state['evidence_sha256'])
            or not isinstance(state['traversals'], dict)
            or len(state['traversals']) > MAX_TRAVERSALS):
        raise ValueError('invalid inventory progress')
    fields = {'question_id', 'kinds', 'exhibits', 'page_size', 'traversal_id',
              'last_id', 'rows_returned', 'pages_returned', 'exhausted', 'next_cursor'}
    for key, row in state['traversals'].items():
        if not _digest(key) or not isinstance(row, dict) or set(row) != fields:
            raise ValueError('invalid inventory traversal fields')
        if (not isinstance(row['question_id'], str) or not row['question_id']
                or len(row['question_id']) > 128 or type(row['page_size']) is not int
                or not 1 <= row['page_size'] <= 250):
            raise ValueError('invalid inventory traversal request')
        for name in ('kinds', 'exhibits'):
            if _filters(row[name], name) != row[name]:
                raise ValueError('inventory traversal filters must be normalized')
        request = {name: row[name] for name in ('question_id', 'kinds', 'exhibits', 'page_size')}
        if key != _request_key(request) or row['traversal_id'] != key:
            raise ValueError('inventory traversal does not match its request binding')
        if (type(row['last_id']) is not int or row['last_id'] < -1
                or type(row['rows_returned']) is not int or row['rows_returned'] < 0
                or type(row['pages_returned']) is not int or not 1 <= row['pages_returned'] <= MAX_PAGES
                or type(row['exhausted']) is not bool
                or row['rows_returned'] > row['pages_returned'] * row['page_size']
                or (row['last_id'] == -1) != (row['rows_returned'] == 0)):
            raise ValueError('invalid inventory traversal counters')
        if row['exhausted']:
            if row['next_cursor'] is not None:
                raise ValueError('exhausted inventory traversal cannot have a next cursor')
        elif (row['rows_returned'] != row['pages_returned'] * row['page_size']
              or not isinstance(row['next_cursor'], str)
              or re.fullmatch(re.escape(key) + ':[0-9a-f]{32}', row['next_cursor']) is None):
            raise ValueError('pending inventory traversal requires a valid next cursor')
    return state


def inventory_progress(run_dir, evidence_sha256=None):
    """Read bounded neutral traversal notes; this does not authenticate their author."""
    path = _run(run_dir) / 'inventory-progress.json'
    if path.is_symlink():
        raise ValueError('inventory progress must not be a symlink')
    if not path.exists():
        return {'status': 'unavailable', 'traversals': [], 'limitation': LIMITATION}
    state = _read(path)
    if evidence_sha256 is not None and state.get('evidence_sha256') != evidence_sha256:
        raise ValueError('inventory progress belongs to different evidence')
    return {'status': 'recorded', 'evidence_sha256': state['evidence_sha256'],
            'traversals': list(state['traversals'].values()), 'limitation': LIMITATION}


@contextmanager
def _locked(run_dir):
    path = _run(run_dir) / '.inventory-progress.lock'
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'a') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError('inventory lock must be a regular file')
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def _filters(values, label):
    if values is None:
        return None
    if (not isinstance(values, list) or not 1 <= len(values) <= 32
            or any(not isinstance(value, str) or not value or len(value) > 256 for value in values)):
        raise ValueError(label + ' must be a list of 1–32 nonempty strings, each at most 256 characters')
    return sorted(set(values))


def page(db, run_dir, evidence_sha256, question_id, kinds=None, exhibits=None,
         page_size=100, cursor=None, cell_limit=240):
    """Persist sequential fixed-query traversal; caller holds its database/thread lock."""
    if type(page_size) is not int or not 1 <= page_size <= 250:
        raise ValueError('page_size must be an integer from 1 to 250')
    if not isinstance(question_id, str) or not question_id or len(question_id) > 128:
        raise ValueError('question_id must name a public question')
    if cursor is not None and (not isinstance(cursor, str) or len(cursor) > 256):
        raise ValueError('invalid inventory cursor')
    request = {'question_id': question_id, 'kinds': _filters(kinds, 'kinds'),
               'exhibits': _filters(exhibits, 'exhibits'), 'page_size': page_size}
    if not _digest(evidence_sha256):
        raise ValueError('invalid inventory evidence digest')
    key = _request_key(request)
    path = _run(run_dir) / 'inventory-progress.json'
    with _locked(run_dir):
        if path.is_symlink():
            raise ValueError('inventory progress must not be a symlink')
        state = _read(path) if path.exists() else {
            'schema_version': 1, 'evidence_sha256': evidence_sha256, 'traversals': {}}
        if state.get('evidence_sha256') != evidence_sha256:
            raise ValueError('inventory progress belongs to different evidence')
        previous = state['traversals'].get(key)
        if previous is None:
            if cursor is not None:
                raise ValueError('foreign or invalid inventory cursor')
            if len(state['traversals']) >= MAX_TRAVERSALS:
                raise ValueError('inventory traversal limit reached')
            previous = {**request, 'traversal_id': key, 'last_id': -1,
                        'rows_returned': 0, 'pages_returned': 0, 'exhausted': False, 'next_cursor': None}
        elif previous['exhausted'] or cursor is None or cursor != previous['next_cursor']:
            raise ValueError('stale, foreign, or exhausted inventory cursor; use the saved next_cursor')
        if previous['pages_returned'] >= MAX_PAGES:
            raise ValueError('inventory page limit reached; traversal remains incomplete')
        predicates, parameters = ['id > ?'], [previous['last_id']]
        for field in ('kind', 'exhibit'):
            values = request['kinds' if field == 'kind' else 'exhibits']
            if values is not None:
                predicates.append(field + ' IN (' + ','.join('?' for _ in values) + ')')
                parameters.extend(values)
        sql = 'SELECT * FROM facts WHERE ' + ' AND '.join(predicates) + ' ORDER BY id LIMIT ?'
        parameters.append(page_size + 1)
        result = db.execute(sql, parameters)
        try:
            columns = [column[0] for column in result.description]
            rows = result.fetchmany(page_size + 1)
        finally:
            result.close()
        exhausted = len(rows) <= page_size
        rows = rows[:page_size]
        next_cursor = None if exhausted else key + ':' + uuid.uuid4().hex
        progress = {**previous, 'last_id': rows[-1][0] if rows else previous['last_id'],
                    'rows_returned': previous['rows_returned'] + len(rows),
                    'pages_returned': previous['pages_returned'] + 1,
                    'exhausted': exhausted, 'next_cursor': next_cursor}
        state['traversals'][key] = progress
        encoded = json.dumps(state, sort_keys=True, ensure_ascii=False)
        if len(encoded.encode('utf-8')) + 1 > MAX_BYTES:
            raise ValueError('inventory progress exceeds its size bound')
        temporary = Path(run_dir) / ('.inventory-' + uuid.uuid4().hex + '.json')
        try:
            with temporary.open('x', encoding='utf-8') as stream:
                stream.write(encoded + '\n')
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
        return {**render_rows(columns, rows, cell_limit), 'status': 'page',
                'evidence_sha256': evidence_sha256, 'progress': progress,
                'next_cursor': next_cursor, 'exhausted': exhausted, 'limitation': LIMITATION}
