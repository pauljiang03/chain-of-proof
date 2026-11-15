"""Typed EVTX record fields; source descriptions do not certify physical actions.

The reviewed Dissect adapter maps TimeCreated_SystemTime to ``ts`` and exposes
EventRecordID as text. That one adapter may decode canonical decimal record IDs;
this is a representation conversion, not authentication of the event or its claims.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import PurePath, PureWindowsPath
import re

from .attributes import emit_attribute
from .source_scope import merge_scope, subject_scope

# Provider/channel membership is explicit; EventID alone is never sufficient.
CHANNELS = {
    'microsoft-windows-security-auditing': 'security',
    'microsoft-windows-eventlog': 'security',
    'eventlog': 'system',
    'microsoft-windows-kernel-general': 'system',
    'microsoft-windows-kernel-power': 'system',
    'microsoft-windows-power-troubleshooter': 'system',
    'user32': 'system',
    'microsoft-windows-winlogon': 'system',
    'microsoft-windows-terminalservices-localsessionmanager':
        'microsoft-windows-terminalservices-localsessionmanager/operational',
    'microsoft-windows-user profiles service': 'microsoft-windows-user profile service/operational',
    'microsoft-windows-diagnostics-performance': 'microsoft-windows-diagnostics-performance/operational',
}
TIME_MEANING = ('event TimeCreated (parser ts): when this event record was timestamped; '
                'not an independently verified action, crash, power transition or embedded performance time')


def _text(value, name, limit=4096):
    if not isinstance(value, str) or not value or len(value) > limit or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError(name + ' is not bounded literal source text')
    return str(value)


def _integer(value, name, maximum, *, parser_text=False):
    raw = value
    if isinstance(value, int) and not isinstance(value, bool):
        number, conversion = int(value), 'native source integer'
    elif parser_text and isinstance(value, str) and re.fullmatch(r'[1-9][0-9]{0,19}', value):
        number, conversion = int(value), 'canonical decimal EventRecordID text from the reviewed target.evtx adapter'
    else:
        raise ValueError(name + ' is not a supported native integer representation')
    if not 1 <= number <= maximum:
        raise ValueError(name + ' is outside its positive source integer range')
    return number, {'raw_value': raw, 'conversion': conversion}


def _source_path(value):
    if isinstance(value, PurePath):
        value = str(value)
    text = _text(value, 'source path', 32768)
    if text != text.strip() or not text.casefold().endswith('.evtx'):
        raise ValueError('source path is not an explicit EVTX file locator')
    win = PureWindowsPath(text)
    if not win.is_absolute() and not text.startswith('/') and not text.casefold().startswith(('sysvol/', 'sysvol\\')):
        raise ValueError('source path has no concrete filesystem root')
    if '..' in text.replace('\\', '/').split('/'):
        raise ValueError('source path contains unresolved parent traversal')
    return text


def emit_event_attributes(out, ev, record, *, parser_record_id_text=False, parser_row_ordinal=None):
    """Return whether a reviewed event emitted typed fields; never revise legacy rows."""
    from .system import SESSION_EVENTS, PERFORMANCE
    if not isinstance(record, dict):
        return False
    provider, channel = record.get('Provider_Name'), record.get('Channel')
    if not isinstance(provider, str) or not isinstance(channel, str):
        return False
    low = provider.casefold()
    if CHANNELS.get(low) != channel.casefold():
        return False
    # Establish the native event-ID type before selecting its description.
    raw_eid = record.get('EventID')
    if not isinstance(raw_eid, int) or isinstance(raw_eid, bool):
        ev.problem('typed event source', ValueError('EventID must be a native integer'))
        return False
    hit = SESSION_EVENTS.get((low, int(raw_eid)))
    performance = low == 'microsoft-windows-diagnostics-performance' and int(raw_eid) in PERFORMANCE
    if not hit and not performance:
        return False
    try:
        provider, channel = _text(provider, 'Provider_Name'), _text(channel, 'Channel')
        event_id, event_id_locator = _integer(raw_eid, 'EventID', 0xffffffff)
        record_id, record_id_locator = _integer(record.get('EventRecordID'), 'EventRecordID', 0xffffffffffffffff,
                                               parser_text=parser_record_id_text)
        if parser_row_ordinal is not None:
            parser_row_ordinal, _ = _integer(parser_row_ordinal, 'parser row ordinal', 0x7fffffffffffffff)
        source = _source_path(record.get('source'))
        stamp = record.get('ts')
        if not isinstance(stamp, datetime) or stamp.tzinfo is None or stamp.utcoffset() is None:
            raise ValueError('event TimeCreated must be a native timezone-aware datetime')
        recorded_time = stamp.astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')
        if type(out.examined_at) is not int or out.examined_at <= 0:
            raise ValueError('typed event observations require positive examination time')
        common = merge_scope(out.common)
        scope = subject_scope(common)
        if any(not isinstance(value, str) or not value.strip() or value.strip().casefold() == 'unknown' for value in scope):
            raise ValueError('typed event observations require explicit image, exhibit, snapshot and variant')
        if hit:
            _, account_field, description = hit
        else:
            account_field = None
            description = PERFORMANCE[event_id][2]
        if low == 'eventlog' and event_id in (6005, 6006):
            description += '; service start/stop does not establish a machine power transition'
        if low == 'microsoft-windows-kernel-power' and event_id == 41:
            description += '; the record timestamp is not the prior crash or power-loss time'
        base = dict(common, artifact=f'{source} record {record_id}', source_path=source,
                    parser='extractor.event_attributes', event_id=event_id, event_record_id=record_id,
                    provider=provider, channel=channel, parser_time_created=stamp.isoformat(),
                    parser_field_mapping='dissect.target EVTX TimeCreated_SystemTime -> ts',
                    parser_timestamp_resolution_us=1,
                    parser_timestamp_precision='Python datetime microseconds; original finer XML precision is not retained by this interface',
                    record_id_representation=record_id_locator,
                    limitation='literal reviewed event fields; not source authenticity, physical-user identity or independent action proof')
        values = [
            ('provider', provider, 'Provider_Name', {'raw_value': provider}),
            ('channel', channel, 'Channel', {'raw_value': channel}),
            ('event_id', event_id, 'EventID', event_id_locator),
            ('record_id', record_id, 'EventRecordID', record_id_locator),
            ('recorded_time', recorded_time, 'TimeCreated_SystemTime (ts)',
             {'parser_value': stamp.isoformat(), 'conversion': 'aware parsed TimeCreated to UTC ISO at microsecond precision; not the original XML timestamp text and no embedded event-data timestamp substitution'}),
            ('description', 'The source event record reports: ' + description, 'Provider_Name/Channel/EventID',
             {'derivation': 'reviewed provider/channel/event-ID description'}),
            ('time_meaning', TIME_MEANING, 'TimeCreated_SystemTime (ts)',
             {'derivation': 'fixed meaning of the timestamp field'}),
        ]
        if account_field:
            if account_field.startswith('sid:'):
                fields = [('account_sid', account_field[4:])]
            else:
                fields = [('account_name', account_field)]
                if low == 'microsoft-windows-security-auditing':
                    fields.append(('account_sid', 'TargetUserSid'))
            for suffix, field in fields:
                raw = record.get(field)
                if raw is None or raw == '':
                    continue
                try:
                    text = _text(raw, field)
                    if suffix == 'account_sid' and not re.fullmatch(r'S-1-[0-9]+(?:-[0-9]+){1,15}', text):
                        raise ValueError(field + ' is not literal SID syntax')
                    values.append((suffix, text, field, {'raw_value': text, 'conversion': 'literal source text; no lookup or domain stripping'}))
                except ValueError as error:
                    ev.problem(base['artifact'] + ' ' + field, error)
        selected_digest = hashlib.sha256(json.dumps(values, ensure_ascii=True, sort_keys=True,
                                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()
        # Record IDs and timestamps can repeat in malformed or repeated records.
        # Retain iterator occurrence and bind every selected literal field so two
        # conflicting records cannot contribute attributes to one source tuple.
        subject = json.dumps(scope + [source, record_id, provider, channel, event_id, recorded_time,
                                      parser_row_ordinal, selected_digest],
                             ensure_ascii=True, separators=(',', ':'))
        base.update(parser_row_ordinal=parser_row_ordinal,
                    parser_row_ordinal_scope='position in this target.evtx iterator; not a byte offset',
                    selected_fields_sha256=selected_digest,
                    selected_fields_hash_scope='selected typed values and source-field locators; not a full raw event or log hash')
        for suffix, value, field, locator in values:
            emit_attribute(ev, subject, 'event.' + suffix, value, out.examined_at,
                           **dict(base, source_field=field, field_locator=locator))
        return True
    except (ValueError, TypeError, OverflowError) as error:
        ev.problem('typed event source', error)
        return False
