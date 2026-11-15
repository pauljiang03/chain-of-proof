"""Key findings in plain sentences.

Every sentence is a count or a value read from evidence records that findings stored as
verified cite. Nothing here is a new finding: no sentence says who did something, or why.
Which records are named is decided by record type and by the rule-based tags the readers
wrote (watch-list search, confidential marker, matching file), never by a model.

The wording follows the writing rules of ASD-STE100 Simplified Technical English: short
sentences, one statement in each sentence, simple tenses, the same word for the same thing.
It was written to those rules by hand and has not been run through an STE checker.
"""
from __future__ import annotations

import re
from collections import Counter

from . import brief

_BROWSERS = {'chrome': 'Chrome', 'iexplore': 'Internet Explorer', 'firefox': 'Firefox', 'edge': 'Edge', 'safari': 'Safari'}
_SERVICES = {'google drive': 'Google Drive', 'outlook e-mail': 'Outlook e-mail', 'icloud': 'iCloud', 'dropbox': 'Dropbox', 'onedrive': 'OneDrive'}
_UNALLOCATED = 'unallocated space of device'
_SAME = 'same size and last-modified time as a file elsewhere'


def _s(value):
    """One clean line of text, or '' for anything that is not text."""
    return ' '.join(value.split()) if isinstance(value, str) else ''


def _obj(entry):
    return _s(entry['row'].get('obj_text'))


def _aux(entry):
    return _s(entry['row'].get('aux_text'))


def _prov(entry):
    value = entry['row'].get('prov')
    return value if isinstance(value, dict) else {}


def _base(path):
    return re.split(r'[\\/]', path.rstrip('\\/'))[-1]


def _extension(name):
    match = re.search(r'\.([A-Za-z0-9]{1,8})$', name)
    return match.group(1).lower() if match else ''


def _n(count, one, many):
    return f'{count:,} {one if count == 1 else many}'


def _join(items, most=6, quote=False):
    """'a, b and c', with the rest counted when the list is long."""
    shown = [('"' + item + '"') if quote else item for item in items[:most]]
    rest = len(items) - len(shown)
    if rest > 0:
        return ', '.join(shown) + f' and {rest:,} more'
    return shown[0] if len(shown) == 1 else ', '.join(shown[:-1]) + ' and ' + shown[-1]


def _distinct(values):
    """Values in first-seen order, compared without case."""
    seen, out = set(), []
    for value in values:
        if value and value.lower() not in seen:
            seen.add(value.lower())
            out.append(value)
    return out


class _Case:
    """The cited records of the chosen verified findings, grouped by record type."""

    def __init__(self, run, ids):
        findings = brief.verified(run)
        if ids is not None:
            wanted = {str(value) for value in ids}
            findings = [row for row in findings if str(row.get('finding_id')) in wanted]
        where = brief.zone(brief.cited(brief.verified(run)))   # one clock for the whole case, also for a selection
        self.findings = findings
        self.records = brief.cited(findings)
        self.stamp = {id(entry): stamp for stamp, entry in brief.timed(self.records)}
        self.tz = brief.clock(where['name']) if where else None
        self.zone = where['name'] if where and self.tz is not None else None
        self.kinds = {}
        for entry in self.records:
            kind = entry['row'].get('kind')
            if isinstance(kind, str):
                self.kinds.setdefault(kind, []).append(entry)

    def of(self, kind):
        """Records of one type, oldest first; records without a source time come last."""
        return sorted(self.kinds.get(kind, ()), key=lambda entry: (id(entry) not in self.stamp, self.stamp.get(id(entry), 0)))

    def times(self, entries):
        return sorted(self.stamp[id(entry)] for entry in entries if id(entry) in self.stamp)

    def at(self, stamp):
        moment = brief.moment(stamp, self.tz)
        return f'{moment:%Y-%m-%d %H:%M}' if moment is not None else ''

    def period(self, entries):
        """' on 2015-03-24, from 15:47 to 16:53' — or '' when the records carry no source time."""
        stamps = self.times(entries)
        if not stamps:
            return ''
        first, last = brief.moment(stamps[0], self.tz), brief.moment(stamps[-1], self.tz)
        if first is None or last is None:
            return ''
        if f'{first:%Y-%m-%d %H:%M}' == f'{last:%Y-%m-%d %H:%M}':
            return f' on {first:%Y-%m-%d} at {first:%H:%M}'
        if first.date() == last.date():
            return f' on {first:%Y-%m-%d}, from {first:%H:%M} to {last:%H:%M}'
        return f' from {first:%Y-%m-%d %H:%M} to {last:%Y-%m-%d %H:%M}'

    def account(self, entries):
        """The one account every one of these records names, or ''."""
        names = {_s(_prov(entry).get('account')) for entry in entries}
        return names.pop() if len(names) == 1 and '' not in names else ''


def _point(key, title, sentences, entries):
    sentences = [sentence for sentence in sentences if sentence]
    if not sentences:
        return None
    findings = set()
    for entry in entries:
        findings |= entry['findings']
    return {'key': key, 'title': title, 'sentences': sentences, 'records': len({id(entry) for entry in entries}),
            'findings': len(findings), '_entries': list(entries)}


def _merge(key, title, *points):
    """Two short topics under one heading, so the list stays short."""
    points = [point for point in points if point]
    return _point(key, title, [sentence for point in points for sentence in point['sentences']],
                  [entry for point in points for entry in point['_entries']])


def _computer(case):
    rows = case.of('systemSetting')
    values = {}
    for entry in rows:
        if _aux(entry) and _aux(entry) != '(none)':
            values.setdefault(_obj(entry).lower(), []).append(_aux(entry))
    out, used = [], []
    for name, text in (('computer name', 'The computer name is {}.'), ('operating system', 'The operating system is {}.'),
                       ('registered owner', 'The registered owner is "{}".'), ('time zone', 'The time zone setting is {}.'),
                       ('network address', 'The network address is {}.')):
        found = _distinct(sorted(values.get(name, ()), key=lambda value: (value != value.upper(), value)))
        if len(found) == 1:
            out.append(text.format(found[0]))
        elif found:
            out.append(f'The records show {len(found)} values for the {name}: {_join(found, 4)}.')
        if found:
            used += [entry for entry in rows if _obj(entry).lower() == name]
    return _point('computer', 'Computer', out, used)


def _accounts(case):
    rows = case.of('accountSeen')
    groups = {}
    for entry in rows:
        groups.setdefault(_aux(entry).lower(), []).append(_obj(entry))
    out = []
    local = _distinct(sorted(groups.pop('windows local account', ()), key=str.lower))
    if local:
        out.append(f'The computer has {_n(len(local), "local account", "local accounts")}: {_join(local, 8)}.')
    for kind in sorted(groups):
        names = _distinct(sorted(groups[kind], key=str.lower))
        if kind and names:
            label = _SERVICES.get(kind, kind)
            out.append(f'The records show the {label} {"account" if len(names) == 1 else "accounts"} {_join(names, 3)}.')
    return _point('accounts', 'Accounts', out, rows)


def _devices(case):
    """One row for each storage device: what it is, its volume, and when it was connected."""
    inserts, volumes, seen = case.of('usbInsert'), case.of('volumeOnDevice'), case.of('volumeSeen')
    labels = {}
    for entry in seen:
        labels.setdefault(_aux(entry).upper(), []).append(_obj(entry))
    table = {}
    for entry in inserts:
        row = table.setdefault(_obj(entry), {'serial': _obj(entry), 'device': '', 'item': '', 'volume': [], 'label': [], 'stamps': [], 'usb': True})
        match = re.search(r'Ven_([^&]+)&Prod_([^&]+)', _s(_prov(entry).get('device')))
        if match and not row['device']:
            row['device'] = (match.group(1) + ' ' + match.group(2)).replace('_', ' ').strip()
        if id(entry) in case.stamp:
            row['stamps'].append(case.stamp[id(entry)])
    for entry in volumes:
        row = table.setdefault(_obj(entry), {'serial': '', 'device': _obj(entry), 'item': '', 'volume': [], 'label': [], 'stamps': [], 'usb': False})
        prov, serial = _prov(entry), _aux(entry).upper()
        row['item'] = row['item'] or _s(prov.get('exhibit'))
        if serial and serial not in row['volume']:
            row['volume'].append(serial)
            row['label'] += labels.get(serial, []) or ([_s(prov.get('volume_label'))] if _s(prov.get('volume_label')) else [])
    rows = []
    for row in table.values():
        stamps = sorted(row['stamps'])
        if not row['usb'] and row['item'] and row['device'].endswith(row['item']):
            row['device'] = row['device'][:-len(row['item'])].strip()   # 'disc RM#3' beside the item RM#3 says it twice
        rows.append({'item': row['item'], 'device': row['device'], 'serial': row['serial'],
                     'label': _join(_distinct(row['label']), 2) if row['label'] else '',
                     'volume': _join(row['volume'], 2) if row['volume'] else '',
                     'first': case.at(stamps[0]) if stamps else '',
                     'last': case.at(stamps[-1]) if stamps and case.at(stamps[-1]) != case.at(stamps[0]) else '',
                     'usb': row['usb'], 'order': stamps[0] if stamps else float('inf')})
    rows.sort(key=lambda row: (row['order'], row['item'], row['serial']))
    for row in rows:
        del row['order']
    usb = [row for row in rows if row.pop('usb')]
    out = [f'The computer records show connections of {_n(len(usb), "USB storage device", "USB storage devices")}.'] if usb else []
    if rows and not usb:
        out.append(f'The records identify {_n(len(rows), "storage device", "storage devices")}.')
    return _point('devices', 'Storage devices', out, inserts + volumes + seen), rows


def _disc(case):
    rows = case.of('cdBurn')
    if not rows:
        return None
    return _point('disc', 'Disc', [f'The records show {_n(len(rows), "trace", "traces")} of disc writing{case.period(rows)}.'], rows)


def _folders(case):
    rows = case.of('folderOpened')
    shares, drives = Counter(), Counter()
    for entry in rows:
        path = _obj(entry)
        if path.startswith('\\\\'):
            parts = path.lstrip('\\').split('\\')
            if len(parts) >= 2:
                shares['\\\\' + parts[0] + '\\' + parts[1]] += 1
        elif re.match(r'^[A-Za-z]:\\', path) and path[0].upper() != 'C':
            drives[path[0].upper() + ':'] += 1
    out, used = [], []
    for share, count in sorted(shares.items(), key=lambda pair: (-pair[1], pair[0]))[:2]:
        part = [entry for entry in rows if _obj(entry).startswith(share)]
        who = case.account(part)
        subject = f'The account "{who}"' if who else 'A user account'
        out.append(f'{subject} opened {_n(count, "folder", "folders")} on the network location {share}.')
        used += part
    if drives:
        total = sum(drives.values())
        out.append(f'The records also show {_n(total, "opened folder", "opened folders")} on {"drive" if len(drives) == 1 else "drives"} '
                   f'{_join(sorted(drives), 5)}.')
        used += [entry for entry in rows if re.match(r'^[A-Za-z]:\\', _obj(entry)) and _obj(entry)[0].upper() != 'C']
    return _point('folders', 'Folders', out, used)


def _files(case):
    tags = case.of('tag')
    marked = [entry for entry in tags if _aux(entry).lower() == 'confidential']
    same = [entry for entry in tags if _aux(entry).lower().startswith(_SAME)]
    renames = case.of('fileRenamed')
    out, used = [], []
    if marked:
        named = [_base(_obj(entry)) for entry in marked if _extension(_base(_obj(entry)))]
        out.append(f'{_n(len(marked), "path contains", "paths contain")} the confidential-project marker.')
        if named:
            out.append(f'One example is {named[0]}.')
        used += marked
    if same:
        out.append(f'{_n(len(same), "file entry has", "file entries have")} the same size and last-modified time as a file in a different location.')
        used += same
    changed = [entry for entry in renames
               if _extension(_base(_obj(entry))) and _extension(_base(_aux(entry)))
               and _extension(_base(_obj(entry))) != _extension(_base(_aux(entry)))]
    if renames:
        out.append(f'The file system journal shows {_n(len(renames), "file rename", "file renames")}.')
        used += renames
    if changed:
        names = {_base(_obj(entry)).lower() for entry in marked}
        first = next((entry for entry in changed if _base(_obj(entry)).lower() in names), changed[0])
        out.append(f'{_n(len(changed), "rename", "renames")} changed the file name extension.')
        out.append(f'One example: {_base(_obj(first))} became {_base(_aux(first))}.')
    return _point('files', 'Files', out, used)


def _recovered(case):
    rows = [entry for entry in case.of('fileCreated') if _aux(entry).lower().startswith(_UNALLOCATED)]
    items = Counter(_s(_prov(entry).get('exhibit')) or 'an item without a label' for entry in rows)
    out = [f'The unallocated space of {item} contains {_n(count, "recovered file entry", "recovered file entries")}.'
           for item, count in sorted(items.items())[:4]]
    return _point('recovered', 'Recovered entries', out, rows)


def _web(case):
    rows = case.of('webSearch')
    if not rows:
        return None
    browsers = _distinct([_BROWSERS.get(_aux(entry).lower(), _aux(entry)) for entry in rows])
    out = [f'The browser history contains {_n(len(rows), "web search", "web searches")}'
           + (f' ({_join(browsers, 3)})' if browsers else '') + f'{case.period(rows)}.']
    watched = [entry for entry in case.of('tag') if _aux(entry).lower() == 'watch-list-search']
    used = list(rows)
    if watched:
        wanted = {_obj(entry).lower() for entry in watched}
        ordered = _distinct([_obj(entry) for entry in rows if _obj(entry).lower() in wanted])
        ordered += [term for term in _distinct(sorted(_obj(entry) for entry in watched)) if term.lower() not in {t.lower() for t in ordered}]
        out.append(f'{_n(len(ordered), "search text matches", "different search texts match")} the search watch list.')
        out.append(f'These are examples: {_join(ordered, 5, quote=True)}.')
        used += watched
    return _point('web', 'Web searches', out, used)


def _downloads(case):
    rows = case.of('fileDownloaded')
    names = _distinct([_base(_obj(entry)) for entry in rows])
    if not names:
        return None
    who = case.account(rows)
    subject = f'The account "{who}"' if who else 'A user account'
    out = [f'{subject} downloaded {_n(len(names), "file", "files")}{case.period(rows)}: {_join(names, 6)}.']
    wanted = {name.lower() for name in names}
    runs = [entry for entry in case.of('programRun') if _base(_obj(entry)).lower() in wanted]
    started = {_base(_obj(entry)).lower() for entry in runs}
    if started:
        out.append(f'{len(started)} of these files {"appears" if len(started) == 1 else "appear"} in the records of started programs.')
    return _point('downloads', 'Downloads', out, rows + runs)


def _mail(case):
    rows = case.of('emailSent')
    if not rows:
        return None
    out = [f'The mailbox contains {_n(len(rows), "e-mail message", "e-mail messages")}{case.period(rows)}.']
    ways = Counter(_aux(entry) for entry in rows if re.match(r'^from \S.* to \S', _aux(entry)))
    for way, count in sorted(ways.items(), key=lambda pair: (-pair[1], pair[0]))[:2]:
        out.append(f'{_n(count, "message is", "messages are")} {way}.')
    subjects = _distinct([re.sub(r'^(?:(?:re|fw|fwd)\s*:\s*)+', '', _obj(entry), flags=re.I) for entry in rows])
    if subjects:
        out.append(f'These are the subjects: {_join(subjects, 6, quote=True)}.')
    return _point('mail', 'E-mail', out, rows)


def _cloud(case):
    rows = case.of('cloudFile')
    if not rows:
        return None
    services = Counter(_aux(entry).split(':')[0].strip() for entry in rows)
    service = services.most_common(1)[0][0]
    part = [entry for entry in rows if _aux(entry).split(':')[0].strip() == service]
    names = _distinct([_obj(entry) for entry in part])
    label = _SERVICES.get(service.lower(), service) or 'cloud storage'
    out = [f'The {label} client log shows {_n(len(part), "file event", "file events")} for {_n(len(names), "file", "files")}{case.period(part)}.']
    uploads = sum(1 for entry in part if _aux(entry).lower().endswith('uploaded'))
    if uploads:
        out.append(f'{_n(uploads, "event is an upload", "events are uploads")}.')
    if 0 < len(names) <= 3:
        out.append(f'The file names are: {_join(names, 3)}.')
    return _point('cloud', 'Cloud storage', out, part)


def _deleted(case):
    rows = case.of('fileDeleted')
    if not rows:
        return None
    bin_ = all(_s(_prov(entry).get('artifact')).lower().startswith('recycle bin') for entry in rows)
    subject = 'The Recycle Bin index shows' if bin_ else 'The records show'
    return _point('deleted', 'Deleted files', [f'{subject} {_n(len(rows), "deleted item", "deleted items")}{case.period(rows)}.'], rows)


def _notes(case):
    searches, notes = case.of('localSearch'), case.of('noteText')
    out = []
    for entry in searches[:3]:
        out.append(f'The {_aux(entry) or "local search history"} contains the search text "{_obj(entry)}".')
    for text in _distinct([_obj(entry) for entry in notes])[:2]:
        place = _aux(next(entry for entry in notes if _obj(entry) == text)) or 'note'
        out.append(f'A {place} file contains this text: "{text[:140]}".')
    return _point('notes', 'Search box and notes', out, searches[:3] + notes)


def build(run, ids=None):
    """Plain sentences about what the cited records of verified findings show.

    Returns {'schema_version', 'zone', 'points': [{'key', 'title', 'sentences', 'records',
    'findings'}], 'devices': [...], 'findings'}. With `ids`, only those findings are read.
    """
    case = _Case(run, ids)
    devices_point, devices = _devices(case)
    # What happened comes first; the computer and its accounts close the list as background.
    points = [devices_point, _folders(case), _merge('files', 'Files', _files(case), _recovered(case)), _disc(case), _mail(case),
              _web(case), _downloads(case), _cloud(case), _deleted(case), _notes(case),
              _merge('computer', 'Computer and accounts', _computer(case), _accounts(case))]
    return {'schema_version': 1, 'zone': case.zone, 'findings': len(case.findings),
            'points': [{name: value for name, value in point.items() if name != '_entries'} for point in points if point],
            'devices': devices}
