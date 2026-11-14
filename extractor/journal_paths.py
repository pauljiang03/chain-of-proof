"""Directory-name inference bounded by intact retained USN-v2 byte intervals.

A later OLD_NAME is not historical evidence by itself. It can constrain an earlier
name only inside a byte-contiguous record interval containing no intervening rename,
creation, removal or hard-link transition for that directory identity. Unknown record
versions, missing bytes and unexplained padding break the interval. This describes
recorded journal state, not filesystem creation onset or secure deletion.

USN semantics: https://learn.microsoft.com/en-us/windows/win32/api/winioctl/ns-winioctl-usn_record_v2
"""
from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from dataclasses import dataclass
import hashlib
import struct

PAGE = 4096
OLD, NEW, CREATE, DELETE, HARD_LINK = 0x1000, 0x2000, 0x100, 0x200, 0x10000


def reference(number):
    return number & ((1 << 48) - 1), number >> 48


@dataclass(frozen=True)
class Entry:
    usn: int
    length: int
    own: tuple
    parent: tuple
    name: str
    reason: int
    attributes: int
    filetime: int


def parse_record(raw, offset):
    """Validate one exact v2 record, including its self-reported stream offset."""
    if len(raw) < 60:
        raise ValueError('short USN record')
    size, major, minor, own, parent, usn, ft, reason, _source, _security, attrs, length, start = \
        struct.unpack_from('<IHHQQqQIIIIHH', raw)
    if (major, minor) != (2, 0) or size != len(raw) or size > PAGE or size % 8:
        raise ValueError('unsupported version or invalid USN record length')
    if usn != offset or offset < 0 or offset % 8:
        raise ValueError('USN does not match its aligned stream offset')
    if (start != 60 or not length or length > 510 or length % 2
            or size != (start + length + 7) // 8 * 8):
        raise ValueError('invalid USN filename bounds')
    name = raw[start:start + length].decode('utf-16-le')
    if '\x00' in name:
        raise ValueError('embedded NUL in USN filename')
    return Entry(usn, size, reference(own), reference(parent), name, reason, attrs, ft)


class JournalRanges:
    """Audit bytes visited by a parser. Never bridge an unexplained skipped region."""
    def __init__(self):
        self.blocks = []
        self.membership = {}
        self.directories = defaultdict(list)
        self.non_directory_refs = set()
        self.current = None
        self.last_end = None
        self.rejected = 0
        self.keys = {}

    def capture(self, offset, length, stream):
        try:
            if length < 60 or length > PAGE:
                raise ValueError('invalid USN length')
            if self.last_end is not None and offset < self.last_end:
                raise ValueError('overlapping or out-of-order journal record')
            stream.seek(offset)
            raw = stream.read(length)
            entry = parse_record(raw, offset)
            previous = self.blocks[self.current] if self.current is not None else None
            padding = b''
            if previous is not None and previous['end'] != offset:
                gap = offset - previous['end']
                # The only permitted skipped bytes are zero tail padding to the
                # immediately following page boundary, never a missing whole page.
                if not (0 < gap < PAGE and offset % PAGE == 0
                        and previous['end'] // PAGE == (offset - 1) // PAGE):
                    previous = None
                else:
                    stream.seek(previous['end'])
                    padding = stream.read(gap)
                    if len(padding) != gap or any(padding):
                        previous = None
            if previous is None:
                self.current = len(self.blocks)
                previous = {'start': offset, 'end': offset, 'hash': hashlib.sha256(), 'records': 0}
                self.blocks.append(previous)
                padding = b''
            previous['hash'].update(padding)
            previous['hash'].update(raw)
            previous['end'] = offset + length
            previous['records'] += 1
            self.membership[offset] = self.current
            self.last_end = offset + length
            if entry.attributes & 0x10:
                self.directories[entry.own].append(entry)
            else:
                self.non_directory_refs.add(entry.own)
            return entry
        except (ValueError, UnicodeError, OSError, struct.error):
            self.current = None
            self.rejected += 1
            return None

    def finish(self):
        self.keys = {ref: [entry.usn for entry in entries] for ref, entries in self.directories.items()}

    def same_block(self, a, b):
        return a in self.membership and self.membership.get(a) == self.membership.get(b)

    def span(self, usn):
        block = self.blocks[self.membership[usn]]
        return {'start_offset': block['start'], 'end_offset_exclusive': block['end'],
                'record_count': block['records'], 'sha256': block['hash'].hexdigest()}

    def directory_name(self, ref, usn):
        """Return a preceding name or a safely bounded first future OLD_NAME pair."""
        if ref in self.non_directory_refs:
            return None
        entries = self.directories.get(ref, [])
        index = bisect_right(self.keys.get(ref, []), usn)
        if index:
            previous = entries[index - 1]
            if (self.same_block(previous.usn, usn)
                    and not previous.reason & (DELETE | HARD_LINK)):
                return previous, 'preceding directory observation'
        # A child observation already names this parent identity. Within the
        # intact range, require consistent directory state until the OLD/NEW pair.
        waiting = []
        for position in range(index, len(entries)):
            entry = entries[position]
            if not self.same_block(usn, entry.usn):
                return None
            if entry.reason & (CREATE | DELETE | NEW | HARD_LINK):
                return None
            if entry.reason & OLD:
                if any((e.name, e.parent) != (entry.name, entry.parent) for e in waiting):
                    return None
                if position + 1 >= len(entries):
                    return None
                following = entries[position + 1]
                if (not self.same_block(entry.usn, following.usn)
                        or not following.reason & NEW
                        or following.reason & (OLD | CREATE | DELETE | HARD_LINK)):
                    return None
                return entry, 'future OLD_NAME paired with NEW_NAME within intact journal interval'
            waiting.append(entry)
        return None

    def folder(self, ref, usn, root_reference, seen=()):
        """Resolve a full path or an explicitly incomplete ancestor suffix.

        Each inferred component comes from an exact parent identity. A missing
        higher ancestor never supplies a guessed current-MFT prefix.
        """
        if ref == root_reference:
            return [], True, []
        if ref in seen or len(seen) >= 64:
            return None
        found = self.directory_name(ref, usn)
        if found is None:
            return None
        entry, method = found
        anchor = {'directory_record': ref[0], 'directory_sequence': ref[1],
                  'anchor_usn': entry.usn, 'anchor_name': entry.name,
                  'anchor_parent': list(entry.parent), 'anchor_reason_flags': entry.reason,
                  'method': method, 'intact_range': self.span(usn)}
        above = self.folder(entry.parent, usn, root_reference, seen + (ref,))
        if above is None:
            return [entry.name], False, [anchor]
        components, complete, anchors = above
        return components + [entry.name], complete, anchors + [anchor]
