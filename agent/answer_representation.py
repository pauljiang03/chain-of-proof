"""Display recorded instants in an explicit report time zone.

The report zone is only a display choice; it says nothing about the zone the
source machine used. Naive source values must be interpreted before calling this.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


_ISO = re.compile(
    r'(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})[T ]'
    r'(?P<time>[0-9]{2}:[0-9]{2}:[0-9]{2})'
    r'(?P<fraction>\.[0-9]+)?(?P<offset>Z|[+-][0-9]{2}:[0-9]{2})')


@dataclass(frozen=True)
class TimestampDisplay:
    source_timestamp: str
    source_utc: str
    display_timestamp: str
    report_timezone: str
    fraction_digits: int
    interpretation: str = 'report_display_only'


def _offset_text(offset):
    seconds = int(offset.total_seconds())
    sign = '+' if seconds >= 0 else '-'
    hours, remainder = divmod(abs(seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    # Some historical IANA offsets include seconds; refuse rather than round them.
    if seconds:
        raise ValueError('report timezone has a sub-minute offset at this instant')
    return f'{sign}{hours:02d}:{minutes:02d}'


def render_timestamp(source: str, report_timezone: str) -> TimestampDisplay:
    """Render an explicitly offset instant in an explicit ZoneInfo zone.

    Needs full seconds; T or a space separates date and time. Fractional digits are
    kept exactly. Unknown offsets (-00:00), naive values and leap seconds fail.
    """
    if not isinstance(source, str) or (match := _ISO.fullmatch(source)) is None:
        raise ValueError('source must be a full ISO timestamp with an explicit offset')
    if not isinstance(report_timezone, str) or not report_timezone:
        raise ValueError('report timezone must be an explicit ZoneInfo key')
    try:
        zone = ZoneInfo(report_timezone)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ValueError('invalid report timezone') from error
    offset = match['offset']
    if offset == '-00:00':
        raise ValueError('unknown source offset is not an instant')
    if offset == 'Z':
        source_zone = timezone.utc
    else:
        hours, minutes = int(offset[1:3]), int(offset[4:6])
        if hours >= 24 or minutes >= 60:
            raise ValueError('invalid source UTC offset')
        delta = timedelta(hours=hours, minutes=minutes)
        source_zone = timezone(delta if offset[0] == '+' else -delta)
    try:
        whole = datetime.fromisoformat(match['date'] + 'T' + match['time']).replace(tzinfo=source_zone)
        utc = whole.astimezone(timezone.utc)
        displayed = utc.astimezone(zone)
    except (ValueError, OverflowError) as error:
        raise ValueError('source instant is outside the supported calendar') from error
    fraction = match['fraction'] or ''
    return TimestampDisplay(
        source_timestamp=source,
        source_utc=utc.isoformat(timespec='seconds')[:-6] + fraction + 'Z',
        display_timestamp=displayed.replace(tzinfo=None).isoformat(timespec='seconds')
        + fraction + _offset_text(displayed.utcoffset()),
        report_timezone=report_timezone,
        fraction_digits=len(fraction[1:]),
    )
