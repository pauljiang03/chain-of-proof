"""Bounded committed SQLite WAL view from captured base and adjacent WAL bytes.

Implements SQLite's documented reader/checksum algorithm:
https://sqlite.org/fileformat2.html#wal_file_format
The transient SHM file is not trusted. Invalid/stale tail frames never become
rows; retained uncommitted frames are counted but not applied. Returned bytes
are a derived view, never a replacement for the original source bytes or hash.
"""
from __future__ import annotations

import hashlib
import struct

MAX_BYTES = 256 * 1024 * 1024
MAX_FRAMES = 100000


def _checksum(data, endian, state=(0, 0)):
    s0, s1 = state
    for first, second in struct.iter_unpack(endian + 'II', data):
        s0 = (s0 + first + s1) & 0xffffffff
        s1 = (s1 + second + s0) & 0xffffffff
    return s0, s1


def committed_view(base, wal):
    if (not isinstance(base, bytes) or not isinstance(wal, bytes)
            or not 100 <= len(base) <= MAX_BYTES or len(wal) > MAX_BYTES
            or base[:16] != b'SQLite format 3\0'):
        raise ValueError('SQLite base/WAL bytes are missing, invalid or exceed the limit')
    encoded_size = struct.unpack_from('>H', base, 16)[0]
    page_size = 65536 if encoded_size == 1 else encoded_size
    if page_size < 512 or page_size > 65536 or page_size & (page_size - 1) or len(base) % page_size:
        raise ValueError('SQLite base page size or file length is invalid')
    provenance = dict(sqlite_base_sha256=hashlib.sha256(base).hexdigest(),
                      sqlite_wal_sha256=hashlib.sha256(wal).hexdigest(),
                      sqlite_base_bytes=len(base), sqlite_wal_bytes=len(wal),
                      sqlite_page_size=page_size, sqlite_valid_frames=0,
                      sqlite_commit_frame=0, sqlite_uncommitted_frames=0,
                      sqlite_ignored_tail_bytes=0,
                      wal_policy='captured base plus checksum-valid committed WAL prefix; SHM not trusted')
    if not wal:
        provenance.update(sqlite_view='base_with_empty_wal', sqlite_view_sha256=provenance['sqlite_base_sha256'])
        return base, provenance
    if base[18:20] != b'\x02\x02' or len(wal) < 32:
        raise ValueError('SQLite base is not WAL mode or WAL header is truncated')
    magic, version, wal_page_size, checkpoint, salt1, salt2, check1, check2 = struct.unpack_from('>8I', wal)
    if magic not in (0x377f0682, 0x377f0683) or version != 3007000 or wal_page_size != page_size:
        raise ValueError('SQLite WAL header version, magic or page size is unsupported')
    endian = '<' if magic == 0x377f0682 else '>'
    state = _checksum(wal[:24], endian)
    if state != (check1, check2):
        raise ValueError('SQLite WAL header checksum does not match')
    frame_size = 24 + page_size
    complete = (len(wal) - 32) // frame_size
    if complete > MAX_FRAMES:
        raise ValueError('SQLite WAL frame count exceeds the limit')
    frames, last_commit, pages = [], 0, len(base) // page_size
    reason = None
    for index in range(complete):
        offset = 32 + index * frame_size
        page, database_pages, frame_salt1, frame_salt2, check1, check2 = struct.unpack_from('>6I', wal, offset)
        if (frame_salt1, frame_salt2) != (salt1, salt2):
            reason = 'first frame with salts outside current WAL generation'
            break
        content = wal[offset + 24:offset + frame_size]
        next_state = _checksum(content, endian, _checksum(wal[offset:offset + 8], endian, state))
        if next_state != (check1, check2):
            reason = 'first frame with invalid cumulative checksum'
            break
        # Tail headers are untrusted until their cumulative checksum succeeds.
        # A corrupt trailing page number cannot invalidate earlier commits.
        if not 1 <= page <= 0xfffffffe:
            raise ValueError('SQLite WAL frame page number is invalid')
        if page * page_size > MAX_BYTES or database_pages * page_size > MAX_BYTES:
            raise ValueError('SQLite WAL page or committed database exceeds the byte limit')
        state = next_state
        frames.append((page, offset + 24))
        if database_pages:
            last_commit, pages = len(frames), database_pages
    parsed_end = 32 + len(frames) * frame_size
    if parsed_end < len(wal) and reason is None:
        reason = 'incomplete trailing frame'
    if last_commit:
        view = bytearray(base[:pages * page_size])
        view.extend(bytes(pages * page_size - len(view)))
        for page, offset in frames[:last_commit]:
            if page <= pages:  # A committed truncate can discard earlier pages.
                view[(page - 1) * page_size:page * page_size] = wal[offset:offset + page_size]
        view = bytes(view)
        if view[:16] != b'SQLite format 3\0' or view[16:18] != base[16:18]:
            raise ValueError('committed SQLite WAL view has an invalid database header')
    else:
        view = base
    provenance.update(sqlite_view='committed_wal' if last_commit else 'base_no_committed_wal',
                      sqlite_valid_frames=len(frames), sqlite_commit_frame=last_commit,
                      sqlite_uncommitted_frames=len(frames) - last_commit,
                      sqlite_ignored_tail_bytes=len(wal) - parsed_end,
                      sqlite_ignored_tail_reason=reason,
                      sqlite_checkpoint_sequence=checkpoint, sqlite_wal_salts=[salt1, salt2],
                      sqlite_database_pages=pages, sqlite_view_sha256=hashlib.sha256(view).hexdigest(),
                      sqlite_source_identity=hashlib.sha256(base + wal).hexdigest())
    return view, provenance
