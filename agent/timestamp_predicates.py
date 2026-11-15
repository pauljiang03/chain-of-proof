"""Exact interval tests for recorded timestamps, counted in 100 ns ticks."""
from datetime import date
import re

TICKS_PER_SECOND = 10_000_000
TICKS_PER_DAY = 86400 * TICKS_PER_SECOND
EPOCH = date(1970, 1, 1).toordinal()
SUPPORTED_ROLES = frozenset({'search.index.date_modified'})
STAMP = re.compile(r'(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})'
                   r'(?:\.(\d{1,7}))?(Z|[+-]\d{2}:\d{2})', re.ASCII)


def instant_ticks(value):
    """Return exact 100 ns ticks since 1970 UTC for an instant with an explicit offset.

    Rejects unknown offsets (-00:00), naive times, leap seconds, bad dates and more than
    seven fractional digits.
    """
    match = STAMP.fullmatch(value) if isinstance(value, str) else None
    if not match:
        raise ValueError('timestamp_requires_explicit_offset_and_at_most_100ns_precision')
    year, month, day, hour, minute, second = map(int, match.groups()[:6])
    if hour > 23 or minute > 59 or second > 59:
        raise ValueError('invalid_timestamp_clock')
    try:
        ordinal = date(year, month, day).toordinal()
    except ValueError as error:
        raise ValueError('invalid_timestamp_date') from error
    suffix = match.group(8)
    offset = 0
    if suffix != 'Z':
        if suffix == '-00:00':
            raise ValueError('unknown_timestamp_offset')
        oh, om = int(suffix[1:3]), int(suffix[4:6])
        if oh > 23 or om > 59:
            raise ValueError('invalid_timestamp_offset')
        offset = (oh * 60 + om) * 60 * (1 if suffix[0] == '+' else -1)
    fraction = int((match.group(7) or '').ljust(7, '0'))
    ticks = ((ordinal - EPOCH) * 86400 + hour * 3600 + minute * 60 + second - offset) * TICKS_PER_SECOND + fraction
    if not (date.min.toordinal() - EPOCH) * TICKS_PER_DAY <= ticks < (date.max.toordinal() + 1 - EPOCH) * TICKS_PER_DAY:
        raise ValueError('timestamp_outside_supported_UTC_range')
    return ticks


def parse_interval(spec):
    """Validate explicit [start, stop) bounds without modifying source values."""
    if (not isinstance(spec, dict) or set(spec) != {'mode', 'role', 'start', 'stop'}
            or spec['mode'] != 'recorded_instant_half_open_v1'
            or not isinstance(spec['role'], str) or spec['role'] not in SUPPORTED_ROLES):
        raise ValueError('unsupported_timestamp_interval_policy')
    start, stop = instant_ticks(spec['start']), instant_ticks(spec['stop'])
    if start >= stop:
        raise ValueError('timestamp_interval_requires_increasing_bounds')
    return dict(spec)


def recorded_in_interval(value, *, role, policy):
    """Whether a recorded timestamp lies in the policy's [start, stop) interval. Bad input raises."""
    spec = parse_interval(policy)
    if role != spec['role']:
        raise ValueError('timestamp_role_mismatch')
    tick = instant_ticks(value)
    return instant_ticks(spec['start']) <= tick < instant_ticks(spec['stop'])
