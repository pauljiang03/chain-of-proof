"""A display summary of cited records, not additional certified findings.

Every sentence is a count or a value read from evidence records that findings stored as
verified cite. No identifier, timestamp, label or name match establishes a physical action.
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
    """Literal source text, or '' for anything that is not text.

    Spaces, tabs and line breaks can be significant evidence values. Formatting
    belongs to the display and must not silently rewrite a quoted source value.
    """
    return value if isinstance(value, str) else ''


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
    """Distinct literal values in first-seen order, without case normalization."""
    seen, out = set(), []
    for value in values:
        if value and value not in seen:
            seen.add(value)
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
    for name, text in (('computer name', 'The cited records give the computer name {}.'),
                       ('operating system', 'The cited records name the operating system {}.'),
                       ('registered owner', 'The cited records name the registered owner "{}".'),
                       ('time zone', 'The cited time zone setting is {}.'),
                       ('network address', 'The cited network address value is {}.')):
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
        out.append(f'The cited records contain {_n(len(local), "distinct local-account name", "distinct local-account names")}: {_join(local, 8)}.')
    for kind in sorted(groups):
        names = _distinct(sorted(groups[kind], key=str.lower))
        if kind and names:
            label = _SERVICES.get(kind, kind)
            out.append(f'The records show the {label} {"account" if len(names) == 1 else "accounts"} {_join(names, 3)}.')
    return _point('accounts', 'Accounts', out, rows)


def _devices(case):
    """One row per cited record; matching identifiers never join physical devices."""
    inserts, volumes, seen = case.of('usbInsert'), case.of('volumeOnDevice'), case.of('volumeSeen')
    rows = []
    for entry in inserts + volumes + seen:
        fact, prov = entry['row'], _prov(entry)
        kind = fact['kind']
        stamp = case.at(case.stamp[id(entry)]) if id(entry) in case.stamp else ''
        meaning = _s(prov.get('time_meaning')) or _s(prov.get('timestamp_semantics')) or 'meaning unavailable'
        scope = '; '.join(f'{name}: {_s(prov[name])}' for name in
                          ('exhibit', 'image', 'source_snapshot', 'source_variant') if _s(prov.get(name)))
        rows.append({'record': f'{kind} #{fact.get("id", "unknown")}', 'item': scope,
                     'device': _s(prov.get('device')) if kind == 'usbInsert' else _obj(entry),
                     'serial': _obj(entry) if kind == 'usbInsert' else '',
                     'volume': _aux(entry) if kind != 'usbInsert' else '',
                     'label': _obj(entry) if kind == 'volumeSeen' else _s(prov.get('volume_label')),
                     'recorded_time': (stamp or 'No displayed source time') + '; ' + meaning})
    out = []
    if inserts:
        out.append(f'The cited records include {_n(len(inserts), "USB identifier record", "USB identifier records")}.')
    if volumes or seen:
        out.append(f'The cited records include {_n(len(volumes) + len(seen), "volume record", "volume records")}.')
    return _point('devices', 'Storage devices', out, inserts + volumes + seen), rows


def _disc(case):
    rows = case.of('cdBurn')
    if not rows:
        return None
    return _point('disc', 'Disc', [f'The cited records include {_n(len(rows), "optical-drive record", "optical-drive records")}.',
                                  f'The retained source timestamps fall{case.period(rows)}.' if case.period(rows) else ''], rows)


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
        part = [entry for entry in rows if _obj(entry) == share or _obj(entry).startswith(share + '\\')]
        out.append(f'{_n(count, "cited folder record names", "cited folder records name")} a path under {share}.')
        used += part
    if drives:
        total = sum(drives.values())
        out.append(f'The cited records also contain {_n(total, "folder-path reference", "folder-path references")} with {"drive letter" if len(drives) == 1 else "drive letters"} '
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
        out.append(f'{_n(len(marked), "cited tag record carries", "cited tag records carry")} the confidential label.')
        if named:
            out.append(f'One example is {named[0]}.')
        used += marked
    if same:
        out.append(f'{_n(len(same), "cited tag record carries", "cited tag records carry")} a same-size-and-time label.')
        used += same
    changed = [entry for entry in renames
               if _extension(_base(_obj(entry))) and _extension(_base(_aux(entry)))
               and _extension(_base(_obj(entry))) != _extension(_base(_aux(entry)))]
    if renames:
        out.append(f'The cited records include {_n(len(renames), "file-rename record", "file-rename records")}.')
        used += renames
    if changed:
        names = {_base(_obj(entry)).lower() for entry in marked}
        first = next((entry for entry in changed if _base(_obj(entry)).lower() in names), changed[0])
        out.append(f'{_n(len(changed), "record pairs", "records pair")} file names with different extensions.')
        out.append(f'One recorded name pair: {_base(_obj(first))} and {_base(_aux(first))}.')
    return _point('files', 'Files', out, used)


def _recovered(case):
    rows = [entry for entry in case.of('fileCreated') if _aux(entry).lower().startswith(_UNALLOCATED)]
    items = Counter(_aux(entry) for entry in rows)
    out = [f'{_n(count, "cited file-creation record carries", "cited file-creation records carry")} the recovery-area label "{label}".'
           for label, count in sorted(items.items())[:4]]
    return _point('recovered', 'Recovered entries', out, rows)


def _web(case):
    rows = case.of('webSearch')
    if not rows:
        return None
    browsers = _distinct([_BROWSERS.get(_aux(entry).lower(), _aux(entry)) for entry in rows])
    out = [f'The cited records include {_n(len(rows), "web-search record", "web-search records")}'
           + (f' ({_join(browsers, 3)})' if browsers else '') + '.']
    if case.period(rows):
        out.append(f'The retained source timestamps fall{case.period(rows)}.')
    watched = [entry for entry in case.of('tag') if _aux(entry).lower() == 'watch-list-search']
    used = list(rows)
    if watched:
        wanted = {_obj(entry).lower() for entry in watched}
        ordered = _distinct([_obj(entry) for entry in rows if _obj(entry).lower() in wanted])
        ordered += [term for term in _distinct(sorted(_obj(entry) for entry in watched)) if term not in set(ordered)]
        out.append(f'{_n(len(ordered), "search text matches", "different search texts match")} the search watch list.')
        out.append(f'These are examples: {_join(ordered, 5, quote=True)}.')
        used += watched
    return _point('web', 'Web searches', out, used)


def _downloads(case):
    rows = case.of('fileDownloaded')
    names = _distinct([_base(_obj(entry)) for entry in rows])
    if not names:
        return None
    out = [f'The cited download records name {_n(len(names), "distinct file basename", "distinct file basenames")}: {_join(names, 6)}.']
    if case.period(rows):
        out.append(f'The retained source timestamps fall{case.period(rows)}.')
    # A name match with Prefetch, Shimcache or MuiCache is neither file identity nor execution proof.
    return _point('downloads', 'Download records', out, rows)


def _mail(case):
    rows = case.of('emailSent')
    if not rows:
        return None
    out = [f'The cited records include {_n(len(rows), "e-mail record", "e-mail records")}.']
    if case.period(rows):
        out.append(f'The retained source timestamps fall{case.period(rows)}.')
    ways = Counter(_aux(entry) for entry in rows if re.match(r'^from \S.* to \S', _aux(entry)))
    for way, count in sorted(ways.items(), key=lambda pair: (-pair[1], pair[0]))[:2]:
        out.append(f'{_n(count, "record carries", "records carry")} the address text "{way}".')
    subjects = _distinct([_obj(entry) for entry in rows])
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
    out = [f'The cited {label} client records contain {_n(len(names), "distinct file name", "distinct file names")}.']
    if case.period(part):
        out.append(f'The retained source timestamps fall{case.period(part)}.')
    uploads = sum(1 for entry in part if _aux(entry).lower().endswith('uploaded'))
    if uploads:
        out.append(f'{_n(uploads, "record carries", "records carry")} an uploaded status label.')
    if 0 < len(names) <= 3:
        out.append(f'The file names are: {_join(names, 3)}.')
    return _point('cloud', 'Cloud storage', out, part)


def _deleted(case):
    rows = case.of('fileDeleted')
    if not rows:
        return None
    bin_ = all(_s(_prov(entry).get('artifact')).lower().startswith('recycle bin') for entry in rows)
    subject = 'The Recycle Bin index shows' if bin_ else 'The records show'
    out = [f'{subject} {_n(len(rows), "deletion record", "deletion records")}.']
    if case.period(rows):
        out.append(f'The retained source timestamps fall{case.period(rows)}.')
    return _point('deleted', 'Deletion records', out, rows)


def _notes(case):
    searches, notes = case.of('localSearch'), case.of('noteText')
    out = []
    for entry in searches[:3]:
        out.append(f'The {_aux(entry) or "local search history"} contains the search text "{_obj(entry)}".')
    for text in _distinct([_obj(entry) for entry in notes])[:2]:
        place = _aux(next(entry for entry in notes if _obj(entry) == text)) or 'note'
        label = 'text excerpt (first 140 characters)' if len(text) > 140 else 'text'
        out.append(f'A {place} file contains this {label}: "{text[:140]}".')
    return _point('notes', 'Search box and notes', out, searches[:3] + notes)


def _lead(case):
    """A short paragraph in Simplified Technical English: one fact per sentence, counts and values only."""
    if not case.records:
        return []
    out = []
    items = sorted(_distinct([_s(_prov(entry).get('exhibit')) for entry in case.records if _s(_prov(entry).get('exhibit'))]),
                   key=lambda name: (len(name), name))
    where = f' with {_n(len(items), "exhibit label", "exhibit labels")}: {_join(items, 6)}' if items else ''
    out.append(f'The verified findings cite {_n(len(case.records), "record", "records")}{where}.')
    names = _distinct([_aux(entry) for entry in case.of('systemSetting')
                       if _obj(entry).lower() == 'computer name' and _aux(entry) and _aux(entry) != '(none)'])
    if names:
        out.append(f'The recorded computer name values are {_join(names, 6, quote=True)}.')
    serials = _distinct([_obj(entry) for entry in case.of('usbInsert') if _obj(entry)])
    if serials:
        out.append(f'The records contain {_n(len(serials), "distinct USB identifier", "distinct USB identifiers")}.')
    counts = [(kind, one, many) for kind, one, many in (('emailSent', 'e-mail record', 'e-mail records'),
              ('webSearch', 'web-search record', 'web-search records'),
              ('fileDeleted', 'file-deletion record', 'file-deletion records'), ('cdBurn', 'optical-drive record', 'optical-drive records'))
              if case.of(kind)]
    if counts:
        parts = [_n(len(case.of(kind)), one, many) for kind, one, many in counts]
        out.append('The records include ' + (parts[0] if len(parts) == 1 else ', '.join(parts[:-1]) + ' and ' + parts[-1]) + '.')
        # State the range of cited source timestamps, without asserting activity boundaries.
        stamps = case.times([entry for kind in ('usbInsert', 'emailSent', 'webSearch', 'fileDeleted', 'cdBurn', 'fileDownloaded')
                             for entry in case.of(kind)])
        first, last = (brief.moment(stamps[0], case.tz), brief.moment(stamps[-1], case.tz)) if stamps else (None, None)
        if first is not None and last is not None:
            out.append(f'These source timestamps range from {first:%Y-%m-%d} to {last:%Y-%m-%d}.' if first.date() != last.date()
                       else f'These source timestamps are on {first:%Y-%m-%d}.')
    return out


def build(run, ids=None):
    """Plain sentences about what the cited records of verified findings show.

    Returns {'schema_version', 'zone', 'points': [{'key', 'title', 'sentences', 'records',
    'findings'}], 'devices': [...], 'findings'}. With `ids`, only those findings are read.
    """
    case = _Case(run, ids)
    devices_point, devices = _devices(case)
    # Cited record topics come first; these are not a reconstruction of physical actions.
    points = [devices_point, _folders(case), _merge('files', 'Files', _files(case), _recovered(case)), _disc(case), _mail(case),
              _web(case), _downloads(case), _cloud(case), _deleted(case), _notes(case),
              _merge('computer', 'Computer and accounts', _computer(case), _accounts(case))]
    result = {'schema_version': 1, 'zone': case.zone, 'findings': len(case.findings), 'lead': _lead(case),
            'points': [{name: value for name, value in point.items() if name != '_entries'} for point in points if point],
            'devices': devices}
    metadata = run.get('case') if isinstance(run, dict) and isinstance(run.get('case'), dict) else {}
    overview = _s(metadata.get('case_summary'))
    if overview.strip():
        result['investigator_overview'] = {'text': overview, 'status': 'unverified'}
    return result
