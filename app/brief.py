"""Facts about the examination (exhibits, tools, time zone, key events per day, limits), built only
from the records that verified findings cite. Nothing is inferred, checked or read from disk.

`KINDS` mirrors KINDS in app/static/timeline.js; a test keeps the two identical.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timedelta, timezone

LANES = (('devices', 'Devices & discs'), ('files', 'Files & folders'), ('web', 'Web'),
         ('messages', 'E-mail & cloud'), ('programs', 'Programs'), ('accounts', 'Sign-ins & accounts'),
         ('system', 'System & notes'), ('other', 'Other records'))
# kind: (lane, singular label, plural label, key event?). Key events are chosen by record type, never by a model.
KINDS = {
    'usbInsert': ('devices', 'USB device connected', 'USB device connections', True),
    'volumeSeen': ('devices', 'Storage volume seen', 'storage volumes seen', True),
    'cdBurn': ('devices', 'Disc-burning trace', 'disc-burning traces', True),
    'volumeOnDevice': ('devices', 'Volume on a device', 'volumes on devices', False),
    'unallocatedOnDevice': ('devices', 'Unused space on a device', 'unused-space records', False),
    'fileCreated': ('files', 'File created', 'files created', False),
    'fileModified': ('files', 'File modified', 'files modified', False),
    'fileDeleted': ('files', 'File deleted', 'files deleted', True),
    'fileRenamed': ('files', 'File renamed', 'files renamed', True),
    'fileSeen': ('files', 'File noted by the system', 'files noted by the system', False),
    'lnkTarget': ('files', 'Shortcut target', 'shortcut targets', True),
    'folderOpened': ('files', 'Folder record', 'folder records', False),
    'fileContent': ('files', 'File content read', 'file contents read', False),
    'localSearch': ('files', 'Search typed on the PC', 'searches typed on the PC', True),
    'webVisit': ('web', 'Web page visit', 'web page visits', False),
    'webSearch': ('web', 'Web search', 'web searches', True),
    'fileDownloaded': ('web', 'File downloaded', 'files downloaded', True),
    'emailSent': ('messages', 'E-mail', 'e-mails', True),
    'cloudFile': ('messages', 'Cloud file activity', 'cloud file records', True),
    'programRun': ('programs', 'Program activity', 'program activity records', False),
    'programInstalled': ('programs', 'Program installed', 'programs installed', True),
    'sessionEvent': ('accounts', 'Sign-in or power event', 'sign-in and power events', False),
    'accountSeen': ('accounts', 'Account record', 'account records', False),
    'systemSetting': ('system', 'System setting', 'system settings', False),
    'shadowCopy': ('system', 'Backup snapshot made', 'backup snapshots made', True),
    'noteText': ('system', 'Note', 'notes', True),
    'tag': ('other', 'Label', 'labels', False),
}
DAY = 86400 * 1000000   # microseconds
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_EXAMINED = re.compile(r'\bwhen (?:the image|this source attribute) was examined\b', re.I)
_UNKNOWN_TIME = re.compile(r'^(?:unknown|unspecified|not recorded|unavailable|none|n/a)(?:\b|$)', re.I)
_SOURCE_TIMESTAMPS = {'journal_observation', 'destlist_entry_update'}
_ZONE = re.compile(r'\b(?:Africa|America|Antarctica|Arctic|Asia|Atlantic|Australia|Europe|Indian|Pacific)'
                   r'/[A-Za-z_]+(?:/[A-Za-z_]+)?')
_DIGEST = re.compile(r'image (md5|sha1|sha256)', re.I)
_DIGEST_NAMES = {'md5': 'MD5', 'sha1': 'SHA-1', 'sha256': 'SHA-256'}
# System settings shown beside an exhibit, matched by the record's own label.
_SYSTEM = (('computer name', 'Computer name'), ('operating system', 'Operating system'),
           ('registered owner', 'Registered owner'), ('time zone', 'Time zone setting'))


def _dict(value):
    return value if isinstance(value, dict) else {}


def _list(value):
    return value if isinstance(value, list) else []


def _text(value):
    """A record value as text, or '' when the record gives none."""
    if not isinstance(value, str):
        return ''
    value = ' '.join(value.split())
    return '' if value in ('', '(none)') else value


def _literal(value):
    """Keep exact source values for display; normalization is only for classification."""
    return value if isinstance(value, str) and value != '(none)' else ''


def _natural(label):
    return [int(part) if index % 2 else part.lower() for index, part in enumerate(re.split(r'(\d+)', label))]


def clock(name):
    """The time zone a name stands for, or None when this system does not know it."""
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(name)
    except Exception:   # an unknown name, or no time zone data on this system
        return None


def moment(micro, tz=None):
    """Microseconds since the Unix epoch as a date and time, in UTC or on the given clock."""
    try:
        value = _EPOCH + timedelta(microseconds=micro)
        return value.astimezone(tz) if tz is not None else value
    except (OverflowError, ValueError, TypeError):
        return None


def verified(run):
    return [row for row in _list(_dict(run).get('findings')) if isinstance(row, dict) and row.get('status') == 'verified']


def cited(findings):
    """Distinct cited records; a differing copy of a record is kept as a different record."""
    seen = {}
    for position, finding in enumerate(findings):
        for row in _list(finding.get('cited_facts')):
            if not isinstance(row, dict):
                continue
            key = json.dumps(row, sort_keys=True, ensure_ascii=False, default=str)
            entry = seen.get(key)
            if entry is None:
                entry = seen[key] = {'row': row, 'findings': set()}
            entry['findings'].add(position)
    return list(seen.values())


def _meaning(row):
    return _text(_dict(row.get('prov')).get('time_meaning'))


def _micro(row):
    stamp = row.get('t')
    if isinstance(stamp, float) and stamp.is_integer():
        stamp = int(stamp)
    return stamp if type(stamp) is int and 0 < stamp <= 2 ** 53 - 1 else None


def timed(records):
    """(time, record) for source timestamps with a known meaning, oldest first."""
    events = []
    for entry in records:
        row, meaning = entry['row'], _meaning(entry['row'])
        semantics = _text(_dict(row.get('prov')).get('timestamp_semantics'))
        stamp = _micro(row)
        if semantics == 'examination_observation' or _EXAMINED.search(meaning):
            continue
        if stamp is not None and (semantics in _SOURCE_TIMESTAMPS or (meaning and not _UNKNOWN_TIME.search(meaning))):
            events.append((stamp, entry))
    events.sort(key=lambda pair: pair[0])
    return events


def zone(records):
    """The zone most records say their local times were converted from: {'name', 'records'} or None."""
    named = Counter()
    for entry in records:
        stated = _dict(entry['row'].get('prov')).get('time_zone')
        match = _ZONE.search(stated) if isinstance(stated, str) else None
        if match:
            named[match.group(0)] += 1
    if not named:
        return None
    name, count = sorted(named.items(), key=lambda item: -item[1])[0]
    return {'name': name, 'records': count, 'known': clock(name) is not None}


def busiest(events):
    """The run of dated records with no gap longer than two days that holds the most records."""
    best, start = None, 0
    for index in range(1, len(events) + 1):
        if index == len(events) or events[index][0] - events[index - 1][0] > 2 * DAY:
            if best is None or index - start > best['records']:
                best = {'from': events[start][0], 'to': events[index - 1][0], 'records': index - start}
            start = index
    return best


def by_day(events, period, tz, most=8):
    """Key events per day of a period, on the given clock: the `most` busiest days, in date order."""
    days = {}
    for stamp, entry in events:
        if period is None or not period['from'] <= stamp <= period['to']:
            continue
        when = moment(stamp, tz)
        if when is None:
            continue
        key = when.date().isoformat()
        day = days.setdefault(key, {'date': key, 'records': 0, 'kinds': {}})
        day['records'] += 1
        kind = entry['row'].get('kind')
        spec = KINDS.get(kind) if isinstance(kind, str) else None
        if spec is None or not spec[3]:
            continue
        group = day['kinds'].get(kind)
        if group is None:
            group = day['kinds'][kind] = {'kind': kind, 'one': spec[1], 'many': spec[2], 'count': 0, 'first': stamp,
                                          'last': stamp, 'example': _text(entry['row'].get('obj_text'))}
        group['count'] += 1
        group['last'] = stamp
    listing = sorted(days.values(), key=lambda day: day['date'])
    total = len(listing)
    if total > most:
        listing = sorted(sorted(listing, key=lambda day: -day['records'])[:most], key=lambda day: day['date'])
    return [{'date': day['date'], 'records': day['records'],
             'events': sorted(day['kinds'].values(), key=lambda group: group['first'])} for day in listing], total


def _add(values, value):
    if value and value not in values:
        values.append(value)


def exhibits(everything, chosen):
    """The exhibits the records name. Identity comes from all verified findings; counts from `chosen`."""
    found, unlabelled = {}, 0
    order = lambda entry: json.dumps(entry['row'].get('id'), sort_keys=True, default=str)
    for entry in sorted(everything, key=order):
        row, prov = entry['row'], _dict(entry['row'].get('prov'))
        label = _literal(prov.get('exhibit'))
        if not label:
            continue
        item = found.setdefault(label, {'label': label, 'images': [], 'records': 0, 'findings': set(), 'devices': [],
                                        'volumes': [], 'digests': [], 'acquired': [], 'tools': [], 'system': []})
        _add(item['images'], _literal(prov.get('image')))
        kind, name, value = row.get('kind'), _literal(row.get('obj_text')), _literal(row.get('aux_text'))
        if kind == 'volumeOnDevice':
            _add(item['devices'], name)
            _add(item['volumes'], value)
        elif kind == 'systemSetting' and _DIGEST.fullmatch(name) and value:
            digest = {'algorithm': _DIGEST_NAMES[_DIGEST.fullmatch(name).group(1).lower()], 'value': value,
                      'record': row.get('id'), 'source': _literal(prov.get('artifact')),
                      'stored_by': _literal(prov.get('stored_by'))}
            if digest not in item['digests']:
                item['digests'].append(digest)
            _add(item['acquired'], _literal(prov.get('acquired_as_recorded')))
            _add(item['tools'], _literal(prov.get('acquired_with')))
        elif kind == 'systemSetting' and value:
            for key, title in _SYSTEM:
                if name.lower() == key:
                    known = next((fact for fact in item['system'] if fact['label'] == title), None)
                    if known is None:
                        item['system'].append({'label': title, 'values': [value]})
                    else:
                        _add(known['values'], value)
    for entry in chosen:
        label = _literal(_dict(entry['row'].get('prov')).get('exhibit'))
        if label in found:
            found[label]['records'] += 1
            found[label]['findings'] |= entry['findings']
        else:
            unlabelled += 1
    listing = sorted(found.values(), key=lambda item: _natural(item['label']))
    titles = [title for _, title in _SYSTEM]
    for item in listing:
        item['findings'] = len(item['findings'])
        item['system'].sort(key=lambda fact: titles.index(fact['label']))
        item['digests'].sort(key=lambda digest: (digest['algorithm'], digest['value']))
    return listing, unlabelled


def _tally(values):
    return [{'name': name, 'count': count} for name, count in sorted(Counter(values).items(), key=lambda item: (-item[1], item[0]))]


def limits(counts, listing, where, note):
    """What the counts do not show, in plain sentences built from the same counts."""
    out = [('scope', 'Findings state what the evidence records say. They do not identify who was using a device, or why.')]
    likely, total = counts['likely'], counts['findings']
    if likely:
        out.append(('likely', f'{likely:,} of {total:,} findings rest on a stated rule of thumb and are marked likely. '
                              'The others follow from the records alone.'))
    out.append(('readers', 'The proof check covers the step from records to findings. '
                           'It does not check that the tools read the disk images correctly.'))
    out.append(('coverage', 'Only records cited by an accepted finding are counted. This does not measure how much of each '
                            'device was examined, and the absence of a finding does not show that something did not happen.'))
    digests = [digest for item in listing for digest in item['digests']]
    if not digests:
        out.append(('hashes', 'No image hash value is among the cited records, so image integrity is not shown here.'))
    elif all('not recomputed' in digest['stored_by'] for digest in digests):
        out.append(('hashes', 'Image hash values are the ones the imaging tool stored in the image files. '
                              'They were not recomputed here.'))
    else:
        out.append(('hashes', 'Image hash values are shown as recorded. Each record says how its value was obtained.'))
    if counts['undated']:
        out.append(('undated', f"{counts['undated']:,} of {counts['records']:,} cited records carry no event time "
                               'and are not on the timeline.'))
    if where is None:
        out.append(('zone', 'The records name no time zone for the examined computer, so times are in UTC.'))
    elif not where['known']:
        out.append(('zone', f"The records name the time zone {where['name']}, which this system cannot convert, "
                            'so times are in UTC.'))
    if counts['refused']:
        out.append(('refused', (f"{counts['refused']:,} proposed findings were" if counts['refused'] != 1
                                else '1 proposed finding was') + ' refused by the checker and listed apart. '
                               'A refusal does not show the claim is false.'))
    if note:
        out.append(('note', 'Note stored with this run: ' + note))
    return [{'key': key, 'text': text} for key, text in out]


def build(run, ids=None, days=8):
    """The brief for a run, or for the findings in `ids`; evidence items always cover the whole run."""
    run = _dict(run)
    everyone = verified(run)
    chosen = everyone if ids is None else [row for row in everyone if row.get('finding_id') in set(ids)]
    everything = cited(everyone)
    records = everything if ids is None else cited(chosen)
    events = timed(records)
    where = zone(everything)
    tz = clock(where['name']) if where and where['known'] else None
    period = busiest(events)
    listing, total_days = by_day(events, period, tz, days)
    items, unlabelled = exhibits(everything, records)
    lanes = Counter(KINDS.get(entry['row'].get('kind'), ('other',))[0]
                    if isinstance(entry['row'].get('kind'), str) else 'other' for entry in records)
    likely = sum(1 for row in chosen if row.get('strength') == 'heuristic')
    case = _dict(run.get('case'))
    counts = {'findings': len(chosen), 'recorded': len(everyone), 'firm': len(chosen) - likely, 'likely': likely,
              'refused': len(_list(run.get('rejections'))), 'judgments': len(_list(run.get('conclusions'))),
              'records': len(records), 'dated': len(events), 'undated': len(records) - len(events)}
    return {
        'schema_version': 1,
        'counts': counts,
        'zone': where,
        'range': {'from': events[0][0], 'to': events[-1][0]} if events else None,
        'busiest': period,
        'days': listing,
        'days_total': total_days,
        'activity': [{'key': key, 'name': name, 'records': lanes[key]} for key, name in LANES if lanes[key]],
        'exhibits': items,
        'unlabelled': unlabelled,
        'tools': _tally(text for entry in everything
                        for text in (_text(_dict(entry['row'].get('prov')).get('tool')),) if text),
        'readers': _tally(text for entry in everything
                          for text in (_text(_dict(entry['row'].get('prov')).get('parser')),) if text),
        'checker': {'trust': _tally(_text(row.get('trust_tier')) or 'not stated' for row in chosen),
                    'axioms': _tally(', '.join(str(axiom) for axiom in row['axioms']) or 'none'
                                     if isinstance(row.get('axioms'), list) else 'not stated' for row in chosen),
                    'proposers': _tally(_text(row.get('proposer')) or 'not stated' for row in chosen)},
        'limits': limits(counts, items, where, _text(case.get('note'))),
    }
