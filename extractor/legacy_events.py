"""Service start/stop events (6005/6006) from legacy EVT logs, with UTC second-precision times."""
from __future__ import annotations

from datetime import datetime

from .store import us

MAX_LOG_BYTES = 256 << 20
MAX_RECORDS = 1_000_000
SCOPE = 'EventLog source, event codes 6005 and 6006 only; security events not decoded'
SUPPORTED = {6005: ('startup', 'the Event Log service was started'),
             6006: ('shutdown', 'the Event Log service was stopped')}


def _event(out, record, source):
    if str(record.SourceName).casefold() != 'eventlog':
        return False
    code = record.EventCode
    if code not in SUPPORTED:
        return False
    generated = record.TimeGenerated
    if not isinstance(generated, datetime) or generated.tzinfo is None or generated.utcoffset() is None:
        raise ValueError('EVT TimeGenerated must have an explicit timezone')
    timestamp = us(generated)
    if timestamp < 0 or generated.microsecond:
        raise ValueError('invalid EVT second-resolution generation timestamp')
    if not isinstance(record.RecordNumber, int) or record.RecordNumber < 1:
        raise ValueError('invalid EVT RecordNumber')
    action, meaning = SUPPORTED[code]
    out.add('sessionEvent', timestamp, 1_000_000, action, '',
            artifact=f'{source} record {record.RecordNumber}', source_path=source,
            parser='dissect.eventlog.evt.Evt / extractor.legacy_events',
            source='legacy event log', provider=record.SourceName,
            record_number=record.RecordNumber, event_id=code, raw_event_id=record.EventID,
            computer=record.Computername, event=meaning,
            time_generated=generated.isoformat(), time_written=record.TimeWritten.isoformat(),
            time_meaning='TimeGenerated UTC, when the Event Log service event was generated',
            parser_scope=SCOPE,
            limitation='service start/stop does not establish the exact machine power transition')
    return True


def extract_sessions(out, ev, target):
    """Add session events to system._Out; failures are reported per file."""
    from dissect.eventlog.evt import Evt

    result = {'files': 0, 'records_examined': 0, 'events_emitted': 0,
              'unsupported_records': 0, 'failed_files': 0, 'scope': SCOPE}
    try:
        directory = target.resolve('%windir%/system32/config')
        if not directory.is_dir():
            raise FileNotFoundError('resolved Windows event-log directory is unavailable')
        paths = sorted((path for path in directory.iterdir()
                        if path.is_file() and path.suffix.casefold() == '.evt'), key=lambda p: str(p).casefold())
        if not paths:
            raise FileNotFoundError('no legacy .evt files found in the resolved Windows configuration directory')
    except Exception as error:
        ev.problem('legacy event logs', error)
        result['failed_files'] += 1
        return result
    for path in paths:
        source = str(path).replace('/', '\\')
        result['files'] += 1
        try:
            if path.stat().st_size > MAX_LOG_BYTES:
                raise ValueError(f'EVT file exceeds bounded reader limit of {MAX_LOG_BYTES} bytes')
            with path.open('rb') as stream:
                for ordinal, record in enumerate(Evt(stream), 1):
                    if ordinal > MAX_RECORDS:
                        raise ValueError(f'EVT record limit {MAX_RECORDS} reached; reading stopped early')
                    result['records_examined'] += 1
                    if _event(out, record, source):
                        result['events_emitted'] += 1
                    else:
                        result['unsupported_records'] += 1
        except Exception as error:
            result['failed_files'] += 1
            ev.problem(source + ' (legacy event-log reading stopped early)', error)
    return result
