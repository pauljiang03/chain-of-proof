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
        self.sequences = defaultdict(set)

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
        self.sequences = defaultdict(set)
        for number, sequence in set(self.directories) | self.non_directory_refs:
            self.sequences[number].add(sequence)

    def same_block(self, a, b):
        return a in self.membership and self.membership.get(a) == self.membership.get(b)

    def span(self, usn):
        block = self.blocks[self.membership[usn]]
        return {'start_offset': block['start'], 'end_offset_exclusive': block['end'],
                'record_count': block['records'], 'sha256': block['hash'].hexdigest()}

    def _directory_state(self, ref, usn):
        """Return a supported observation or a precise reason for abstaining.

        An OLD_NAME records the pre-rename name. It cannot establish which name
        applies to a child record interleaved before the corresponding NEW_NAME.
        https://learn.microsoft.com/en-us/windows/win32/api/winioctl/ns-winioctl-usn_record_v2
        """
        if usn not in self.membership:
            return None, 'child_record_outside_validated_interval'
        if ref in self.non_directory_refs:
            return None, 'identity_not_exclusively_directory'
        entries = self.directories.get(ref, [])
        index = bisect_right(self.keys.get(ref, []), usn)
        if index:
            previous = entries[index - 1]
            if self.same_block(previous.usn, usn):
                if previous.reason & OLD:
                    return None, 'rename_transition_in_progress'
                if previous.reason & (DELETE | HARD_LINK):
                    return None, 'prior_removal_or_hard_link_transition'
                return (previous, 'preceding directory observation'), None
        # A child observation already names this parent identity. Within the
        # intact range, require consistent directory state until the OLD/NEW pair.
        waiting = []
        for position in range(index, len(entries)):
            entry = entries[position]
            if not self.same_block(usn, entry.usn):
                return None, 'directory_observation_outside_intact_interval'
            if entry.reason & (CREATE | DELETE | NEW | HARD_LINK):
                return None, 'future_creation_removal_rename_or_link_transition'
            if entry.reason & OLD:
                if any((e.name, e.parent) != (entry.name, entry.parent) for e in waiting):
                    return None, 'conflicting_future_directory_state'
                if position + 1 >= len(entries):
                    return None, 'old_name_without_following_new_name'
                following = entries[position + 1]
                if (not self.same_block(entry.usn, following.usn)
                        or not following.reason & NEW
                        or following.reason & (OLD | CREATE | DELETE | HARD_LINK)):
                    return None, 'old_new_pair_not_validated'
                return (entry, 'future OLD_NAME paired with NEW_NAME within intact journal interval'), None
            waiting.append(entry)
        if not entries:
            variants = self.sequences.get(ref[0], set()) - {ref[1]}
            return None, 'different_reference_sequence_only' if variants else 'no_directory_observation'
        return None, 'future_name_without_bounded_old_new_pair' if waiting else 'directory_observation_outside_intact_interval'

    def directory_name(self, ref, usn):
        """Return a preceding name or a safely bounded first future OLD_NAME pair."""
        return self._directory_state(ref, usn)[0]

    def resolve_folder(self, ref, usn, root_reference, seen=()):
        """Resolve within this stream and retain a diagnostic for any missing prefix.

        Identities here are local (record, sequence) pairs. The caller must bind
        this result to its image/exhibit/full-volume scope before emitting facts.
        No current MFT names, timestamps or unbounded future names are consulted.
        """
        chain, visited = [], set(seen)
        current = ref
        valid_child = usn in self.membership
        reason = None if valid_child else 'child_record_outside_validated_interval'
        while valid_child and current != root_reference:
            if current in visited:
                reason = 'ancestor_cycle'
                break
            if len(visited) >= 64:
                reason = 'ancestor_depth_limit'
                break
            if current[0] == 5 and root_reference is None:
                reason = 'root_identity_unavailable'
                break
            if current[0] == 5 and root_reference is not None:
                reason = 'root_reference_sequence_mismatch'
                break
            found, reason = self._directory_state(current, usn)
            if found is None:
                break
            entry, method = found
            chain.append({'directory_record': current[0], 'directory_sequence': current[1],
                          'anchor_usn': entry.usn, 'anchor_name': entry.name,
                          'anchor_parent': list(entry.parent), 'anchor_reason_flags': entry.reason,
                          'method': method, 'intact_range': self.span(usn)})
            visited.add(current)
            current = entry.parent
        complete = valid_child and current == root_reference and root_reference is not None
        anchors = list(reversed(chain))
        result = {'components': [anchor['anchor_name'] for anchor in anchors],
                  'path_complete': complete, 'anchors': anchors, 'diagnostic': None}
        if complete:
            return result
        entries = self.directories.get(current, [])
        needed = ('A directory name and parent link for this exact record-and-sequence identity '
                  'at the child USN, supported within the same intact journal interval. '
                  'An earlier retained journal, independently bounded historical directory snapshot, '
                  'or valid bounded OLD_NAME/NEW_NAME pair may supply support; present MFT paths '
                  'or a different record sequence do not.')
        if reason == 'ancestor_cycle':
            needed = 'Resolve the conflicting parent-identity cycle from independently consistent historical records; do not splice in a present MFT prefix.'
        elif reason == 'rename_transition_in_progress':
            needed = 'A supported name/parent observation for the child event outside the interleaved OLD_NAME/NEW_NAME transition; neither rename endpoint alone orders that child event.'
        elif reason in ('root_identity_unavailable', 'root_reference_sequence_mismatch'):
            needed = 'The root-directory identity and sequence from the same scoped volume, plus a consistent historical chain to that exact root identity.'
        result['diagnostic'] = {
            'status': 'diagnostic', 'reason': reason or 'root_identity_unavailable',
            'at_usn': usn,
            'missing_ancestor': {'file_record': current[0], 'file_sequence': current[1]},
            'resolved_chain_child_to_root': [
                {'file_record': a['directory_record'], 'file_sequence': a['directory_sequence'],
                 'anchor_usn': a['anchor_usn']} for a in chain],
            'directory_observations_for_identity': len(entries),
            'first_directory_usn': entries[0].usn if entries else None,
            'last_directory_usn': entries[-1].usn if entries else None,
            'other_observed_sequences': sorted(self.sequences.get(current[0], set()) - {current[1]}),
            'child_intact_interval': self.span(usn) if usn in self.membership else None,
            'evidence_needed': needed,
            'scope_requirement': 'same image, exhibit and full NTFS volume serial; scoped identity must include the record sequence',
            'limitation': 'This identifies missing support, not a recovered prefix or proof of absence.'}
        return result

    def folder(self, ref, usn, root_reference, seen=()):
        """Resolve a full path or an explicitly incomplete ancestor suffix.

        Each inferred component comes from an exact parent identity. A missing
        higher ancestor never supplies a guessed current-MFT prefix.
        """
        resolved = self.resolve_folder(ref, usn, root_reference, seen)
        if not resolved['components'] and not resolved['path_complete']:
            return None
        return resolved['components'], resolved['path_complete'], resolved['anchors']
