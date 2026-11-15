"""Standalone HTML for supplied investigation bundles; never verifies or reads files.

`render_html(run)` reproduces the whole bundle. `render_html(run, report_options(...))`
builds an examiner's report: chosen findings, chosen sections and cover details. A
report that leaves anything out says so on its first page.

Reports use a conventional examination structure. Administrative details come from
the report author. Results and source references come from the supplied bundle.
The report prose uses ASD-STE100 writing rules. Source text remains unchanged.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from html import escape
import json
import re

from . import brief, narrative

# Optional parts of a report. The certified findings themselves are always included.
SECTIONS = ('workflow', 'needs', 'judgments', 'evidence', 'proofs', 'activity')
SECTION_LABELS = {'workflow': 'question-by-question plan', 'needs': 'refused proposals',
                  'judgments': 'investigator judgments', 'evidence': 'full evidence records',
                  'proofs': 'Lean proof records', 'activity': 'audit, coverage and history'}
COVER = (
    ('reference', 'Case reference'), ('report_id', 'Report number'), ('report_version', 'Report version'),
    ('examiner', 'Examiner'), ('organisation', 'Organisation'), ('address', 'Organisation address'),
    ('report_date', 'Date of report'), ('requested_by', 'Requested by'), ('request_date', 'Date of request'),
    ('authority', 'Authority for the request'), ('purpose', 'Purpose and scope'),
    ('received', 'Evidence received'), ('submitted_by', 'Submitted by'), ('collection_method', 'Method of receipt or collection'),
    ('additional_items', 'Other submitted items'), ('method_notes', 'Examination procedures'),
    ('disposition', 'Evidence disposition'), ('authorizer', 'Report authorizer'),
    ('impact', 'Incident impact'), ('root_cause', 'Cause of the incident'),
    ('response', 'Response and recovery'), ('recommendations', 'Recommended actions'),
)
COVER_LIMITS = {key: 600 for key in ('purpose', 'additional_items', 'method_notes', 'disposition',
                                    'impact', 'root_cause', 'response', 'recommendations')}
_REQUEST_KEYS = ('requested_by', 'request_date', 'authority', 'purpose')
_INTAKE_KEYS = ('received', 'submitted_by', 'collection_method', 'additional_items')
_INCIDENT_KEYS = ('impact', 'root_cause', 'response', 'recommendations')
_HEADER_KEYS = ('reference', 'report_id', 'report_version', 'examiner', 'organisation', 'address', 'report_date')
MAX_SELECTED = 2000
_FINDING_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}')


def report_options(ids=None, sections=None, reference='', examiner='', organisation='', *, brief=False, **more):
    """Validate what goes into a report. `None` for ids or sections means everything.

    `brief` asks for the short report: the summary, the evidence examined, the limits and the
    sign-off, on one or two printed pages. The findings themselves stay in the stored run.
    """
    if not isinstance(brief, bool):
        raise ValueError('Unknown report length.')
    if ids is not None:
        ids = list(ids)
        if (not 1 <= len(ids) <= MAX_SELECTED or len(set(ids)) != len(ids)
                or not all(isinstance(item, str) and _FINDING_ID.fullmatch(item) for item in ids)):
            raise ValueError(f'Select between 1 and {MAX_SELECTED} distinct finding IDs.')
    if sections is not None:
        sections = list(sections)
        if len(set(sections)) != len(sections) or set(sections) - set(SECTIONS):
            raise ValueError('Unknown report section.')
        sections = frozenset(sections)
    options = {'ids': ids, 'sections': sections, 'brief': brief}
    given = {'reference': reference, 'examiner': examiner, 'organisation': organisation, **more}
    if set(given) - {key for key, _ in COVER}:
        raise ValueError('Unknown cover detail.')
    for key, _ in COVER:
        value = given.get(key, '')
        if (not isinstance(value, str) or len(value) > COVER_LIMITS.get(key, 200)
                or any(ord(c) < 32 or ord(c) == 127 for c in value)):
            raise ValueError('Report fields must be plain text. Use at most 200 characters for identifiers and 600 for narrative fields.')
        options[key] = value.strip()
    return options


_CSS = """
:root, :host { color-scheme: light; --ink:#172c39; --muted:#536674; --line:#d8e1e5;
  --paper:#fff; --wash:#f3f6f7; --accent:#176b57; --warn:#865314; }
* { box-sizing:border-box; }
html { scroll-behavior:smooth; }
.report { margin:0; background:var(--wash); color:var(--ink);
  font:15px/1.65 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
main { max-width:1100px; margin:40px auto; padding:48px 56px; background:var(--paper);
  border:1px solid var(--line); border-radius:12px; }
header { border-top:5px solid var(--accent); padding-top:24px; }
.eyebrow { color:var(--accent); text-transform:uppercase; letter-spacing:.14em;
  font-size:12px; font-weight:750; }
h1 { font-size:36px; line-height:1.2; margin:12px 0 20px; overflow-wrap:anywhere; }
h2 { font-size:24px; margin:0 0 14px; line-height:1.3; }
h3 { font-size:18px; margin:0 0 12px; line-height:1.4; }
h4 { font-size:15px; margin:20px 0 8px; }
p { margin:10px 0; }
section { margin-top:38px; padding-top:28px; border-top:1px solid var(--line); }
article { margin:20px 0; border:1px solid var(--line); border-radius:8px; padding:24px;
  scroll-margin-top:20px; }
a { color:var(--accent); text-decoration-thickness:1px; text-underline-offset:3px; }
nav { display:flex; flex-wrap:wrap; gap:10px 20px; margin:24px 0; font-size:13px; }
.muted, .small { color:var(--muted); }
.small { font-size:13px; }
.notice { padding:14px 18px; border-left:3px solid var(--accent); background:#f0f7f4; }
.warning { border-left-color:var(--warn); background:#fff6e9; }
.badge { display:inline-block; border:1px solid var(--line); padding:2px 9px;
  border-radius:20px; margin:0 5px 8px 0; font-size:12px; font-weight:650; }
.sentence { font-size:18px; line-height:1.65; white-space:pre-wrap; overflow-wrap:anywhere; }
dl { display:grid; grid-template-columns:minmax(140px,1fr) minmax(0,3fr); gap:7px 18px; }
dt { color:var(--muted); }
dd { margin:0; white-space:pre-wrap; overflow-wrap:anywhere; }
pre { background:#f4f6f8; border:1px solid var(--line); border-radius:6px; padding:16px;
  white-space:pre-wrap; overflow-wrap:anywhere; font:12px/1.65 ui-monospace,SFMono-Regular,Consolas,monospace; }
table { width:100%; border-collapse:collapse; font-size:13px; margin:16px 0; }
th,td { text-align:left; padding:10px; border-bottom:1px solid var(--line); vertical-align:top;
  overflow-wrap:anywhere; }
th { color:var(--muted); background:var(--wash); font-weight:650; }
.table-wrap { overflow-x:auto; }
.cited th:first-child, .cited td:first-child { white-space:nowrap; overflow-wrap:normal; }
.cited th:nth-child(2) { width:34%; } .cited th:nth-child(3) { width:30%; }
.lead { font-size:17px; line-height:1.6; }
.keys { margin:0 0 6px; }
.key { display:grid; grid-template-columns:150px minmax(0,1fr); gap:2px 18px; padding:7px 0; border-bottom:1px solid var(--line); break-inside:avoid; }
.key h3 { font-size:14px; margin:0; line-height:1.5; }
.key p { margin:0; line-height:1.5; }
.key table { margin:6px 0 2px; font-size:12px; }
.key th, .key td { padding:4px 8px; white-space:nowrap; overflow-wrap:normal; }
.devices td:nth-child(4) { white-space:normal; overflow-wrap:anywhere; }
@media(max-width:700px) { .key { grid-template-columns:1fr; } }
#summary { container-type:inline-size; }   /* the preview pane is narrower than its window */
@container (max-width:700px) { .key { grid-template-columns:minmax(0,1fr); } .key th,.key td { white-space:normal; }
  .key table { font-size:11px; } .key th,.key td { padding:4px 6px; overflow-wrap:anywhere; } }
/* The short report reads as one or two pages on screen too: bold lead-ins, tight sections. */
@media screen {
  main.brief { padding:28px 34px; font-size:13px; line-height:1.5; } .brief table { font-size:12px; } .brief .small { font-size:12px; }
  .brief header { border-top-width:4px; padding-top:14px; } .brief h1 { font-size:24px; margin:6px 0 10px; }
  .brief h2 { font-size:17px; margin-bottom:8px; } .brief section { margin-top:18px; padding-top:16px; }
  .brief p { margin:6px 0; } .brief dl { gap:3px 16px; } .brief table { margin:8px 0; } .brief th, .brief td { padding:6px 8px; }
  .brief .key { display:block; padding:5px 0; } .brief .key h3 { display:inline; font-size:inherit; line-height:inherit; }
  .brief .key h3::after { content:". "; } .brief .key > div, .brief .key p { display:inline; line-height:inherit; }
  .brief #summary > h3 { font-size:15px; margin:14px 0 4px; }
  .brief .sign { margin:18px 0 8px; } .brief .sign div { min-height:46px; } .brief footer { margin-top:18px; padding-top:12px; }
}
.mono { font:12px/1.5 ui-monospace,SFMono-Regular,Consolas,monospace; overflow-wrap:anywhere; }
.days th:first-child, .days td:first-child { white-space:nowrap; overflow-wrap:normal; }
.exhibits td:last-child { white-space:nowrap; overflow-wrap:normal; }
.exhibits th, .days th { white-space:normal; overflow-wrap:normal; }
.exhibits { table-layout:fixed; }
.exhibits th:first-child { width:24%; }
.exhibits th:nth-child(2) { width:38%; }
.short th:first-child { width:24%; } .short th:nth-child(2) { width:30%; } .short .mono { overflow-wrap:normal; white-space:nowrap; }
.exact-statement { margin:12px 0; border-left:2px solid var(--line); padding-left:14px; }
.exhibits td:last-child { white-space:normal; }
ol { padding-left:22px; } ol li { margin:6px 0; }
.limits { margin:10px 0; padding-left:20px; } .limits li { margin:4px 0; }
code { font:13px ui-monospace,SFMono-Regular,Consolas,monospace; background:var(--wash); padding:1px 5px; border-radius:4px; }
.sign { display:grid; grid-template-columns:2fr 2fr 1fr; gap:28px; margin:30px 0 12px; }
.sign div { display:flex; flex-direction:column; justify-content:space-between; min-height:62px;
  border-bottom:1px solid var(--ink); padding-bottom:6px; }
.sign span { color:var(--muted); font-size:12px; } .sign strong { font-weight:600; min-height:1.4em; }
summary { cursor:pointer; color:var(--muted); font-size:13px; margin:12px 0; }
footer { border-top:1px solid var(--line); padding-top:24px; margin-top:40px; color:var(--muted); font-size:12px; }
@media(max-width:700px) { main { margin:0; padding:24px 18px; border:0; border-radius:0; }
  h1 { font-size:28px; } article { padding:18px; } dl { grid-template-columns:1fr; gap:2px; }
  dd { margin-bottom:9px; } .sign { grid-template-columns:1fr; } }
@media print { @page { margin:18mm; @bottom-right { content:"Page " counter(page) " of " counter(pages);
    font:9pt system-ui,sans-serif; color:#536674; } }
  .report,main { background:#fff; } .sign { break-inside:avoid; }
  .report { font-size:10pt; } main { max-width:none; margin:0; padding:0; border:0; }
  nav { display:none; } h1 { font-size:26pt; } h2 { font-size:18pt; } h3 { font-size:13pt; }
  h1,h2,h3,h4 { break-after:avoid; } section { margin-top:24px; padding-top:18px; }
  article { padding:15px; border-radius:0; } pre { font-size:8pt; overflow:visible; }
  .sentence { font-size:12pt; } .table-wrap { overflow:visible; } tr { break-inside:avoid; }
  details:not([open]) > :not(summary) { display:block !important; }
  .exact-statement > summary { display:block; font-weight:600; color:var(--ink); } a { color:inherit; } .notice { break-inside:avoid; }
  /* The summary is one printed page: small type and tight rows. */
  #summary { font-size:9pt; padding-top:10px; } #summary h2 { font-size:15pt; margin-bottom:4px; }
  .key { display:block; padding:2px 0; line-height:1.4; } .key h3 { display:inline; font-size:9pt; line-height:inherit; }
  .key h3::after { content:". "; } .key > div, .key p { display:inline; line-height:inherit; }
  .key table { font-size:8pt; margin:3px 0 0; } .key th, .key td { padding:2px 6px; }
  #summary > h3 { font-size:11pt; margin:6px 0 2px; } #summary .days { font-size:8.5pt; line-height:1.4; margin:2px 0; }
  #summary .days th, #summary .days td { padding:2px 8px; } #summary > .small { font-size:8pt; line-height:1.35; margin:4px 0 0; }
  /* The short report is one or two printed pages. */
  .brief { font-size:9pt; line-height:1.45; } .brief header { padding-top:10px; }
  .brief h1 { font-size:18pt; margin:4px 0 8px; } .brief h2, .brief #summary h2 { font-size:12pt; margin-bottom:4px; }
  .brief section { margin-top:10px; padding-top:8px; } .brief p { margin:4px 0; } .brief dl { gap:2px 14px; }
  .brief table { font-size:8pt; margin:4px 0; } .brief th, .brief td { padding:3px 8px; }
  .brief .small, .brief .mono, .brief code { font-size:8pt; } .brief .limits { margin:4px 0; } .brief .limits li { margin:2px 0; }
  .brief .sign { margin:12px 0 4px; gap:20px; } .brief .sign div { min-height:40px; }
  .brief footer { margin-top:12px; padding-top:8px; font-size:8pt; }
}
"""


def _object(value):
    return value if isinstance(value, dict) else {}


def _rows(value):
    return value if isinstance(value, list) else []


def _text(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _h(value):
    return escape(_text(value), quote=True)


def _v(mapping, key, missing="Unknown — not supplied"):
    value = mapping.get(key)
    return _h(missing if value is None else value)


def _pre(value, *, source=False):
    content = value if source else json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)
    return '<pre><code>' + _h(content) + '</code></pre>'


def _fields(items):
    return '<dl>' + ''.join('<dt>' + _h(label) + '</dt><dd>' + value + '</dd>'
                           for label, value in items) + '</dl>'


def _details(label, value):
    return '<details><summary>' + _h(label) + '</summary>' + _pre(value) + '</details>'


def _table(headings, rows, kind=''):
    return ('<div class="table-wrap"><table' + (' class="' + kind + '"' if kind else '') + '><thead><tr>'
            + ''.join('<th scope="col">' + _h(h) + '</th>' for h in headings)
            + '</tr></thead><tbody>'
            + ''.join('<tr>' + ''.join('<td>' + cell + '</td>' for cell in row) + '</tr>' for row in rows)
            + '</tbody></table></div>')


def _time(row, tz=None):
    stamp = row.get('t')
    if type(stamp) is not int:
        return _v(row, 't')
    try:
        date = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=stamp)
        exact = _h(date.isoformat().replace('+00:00', 'Z')) + f' ({stamp} microseconds since Unix epoch)'
        # With a case clock: local time first, then the UTC instant exactly as stored.
        return exact if tz is None else _h(_local(date.astimezone(tz))) + '<br><span class="small">' + exact + '</span>'
    except (OverflowError, ValueError):
        return f'{stamp} microseconds since Unix epoch (outside displayable date range)'


def _plural(count, one, many):
    return f'{count:,} ' + (one if count == 1 else many)


def _local(date):
    """A date and time on the case clock, with its offset from UTC written out."""
    offset = date.utcoffset() or timedelta(0)
    minutes = int(offset.total_seconds() // 60)
    sign = '+' if minutes >= 0 else '-'
    return date.strftime('%Y-%m-%d %H:%M:%S') + f' local (UTC{sign}{abs(minutes) // 60:02d}:{abs(minutes) % 60:02d})'


def _day(iso):
    day = datetime.strptime(iso, '%Y-%m-%d')
    return f'{day:%a} {day.day} {day:%b %Y}'


def _span(first, last, tz):
    start, end = brief.moment(first, tz), brief.moment(last, tz)
    if start is None or end is None:
        return ''
    return f'{start:%H:%M}' if (last - first) < 60 * 1000000 else f'{start:%H:%M}–{end:%H:%M}'


# Which event groups a summary day names first. The order is by record type and is the same for every case.
_SUMMARY_ORDER = ('usbInsert', 'cdBurn', 'fileDeleted', 'emailSent', 'fileDownloaded', 'cloudFile', 'webSearch', 'fileRenamed',
                  'localSearch', 'noteText', 'volumeSeen', 'shadowCopy', 'programInstalled', 'lnkTarget')


def _day_events(groups, most=3):
    """The groups one summary row names: picked by record type in a fixed order, shown in time order."""
    rank = {kind: place for place, kind in enumerate(_SUMMARY_ORDER)}
    chosen = sorted(groups, key=lambda group: rank.get(group.get('kind'), len(rank)))[:most]
    return sorted(chosen, key=lambda group: group['first'])


def _exhibits(info, short=False):
    """The evidence items that the findings cite, with the identifiers and hash values in the records."""
    if not info['exhibits']:
        return '<p>The cited evidence records name no exhibit.</p>'
    rows = []
    for item in info['exhibits'] if short else ():   # one or two lines per cell: what identifies the item, and its hash values
        identity = [_h('Device ' + value) for value in item['devices'] if item['label'].lower() not in value.lower()]
        identity += [_h('Volume serial ' + value) for value in item['volumes']]
        if item['system']:
            identity.append(_h(' · '.join(fact['label'] + ': ' + ', '.join(fact['values']) for fact in item['system'])))
        rows.append(('<strong>' + _h(item['label']) + '</strong> ' + _h(', '.join(item['images']))
                     + '<br><span class="small">' + f"{item['records']:,} records in "
                     + _plural(item['findings'], 'finding', 'findings') + '</span>',
                     '<br>'.join(identity) or '—',
                     '<br>'.join('<span class="mono">' + _h(digest['algorithm'] + ' ' + digest['value']) + '</span>'
                                 for digest in item['digests']) or 'No stored hash value in the cited records'))
    if short:
        return _table(('Evidence item and image', 'Identifiers', 'Stored hash values'), rows, 'exhibits short')
    for item in info['exhibits']:
        identity = [_h('Device ' + value) for value in item['devices'] if item['label'].lower() not in value.lower()]
        identity += [_h('Volume serial ' + value) for value in item['volumes']]
        identity += [_h(fact['label'] + ': ' + ', '.join(fact['values'])) for fact in item['system']]
        digests = ['<span class="mono">' + _h(digest['algorithm'] + ' ' + digest['value']) + '</span> <span class="small">(record '
                   + _h(digest['record']) + ')</span>' for digest in item['digests']]
        acquired = [_h('Time as recorded: ' + value) for value in item['acquired']]
        acquired += [_h('Imaging tool as recorded: ' + value) for value in item['tools']]
        rows.append(('<strong>' + _h(item['label']) + '</strong><br>' + _h(', '.join(item['images']))
                     + '<br><span class="small">' + f"{item['records']:,} records in "
                     + _plural(item['findings'], 'finding', 'findings') + '</span>',
                     '<br>'.join(identity + acquired) or '—',
                     '<br>'.join(digests) or 'No stored hash value in the cited records'))
    return _table(('Evidence item and image', 'Identifiers and acquisition', 'Stored hash values'), rows, 'exhibits')


def _short_back(info, case, options):
    """The rest of the short report: the evidence examined, then the method and its limits in a few lines."""
    out = []
    request = _option_fields(options, _REQUEST_KEYS)
    if request:
        out.append('<section id="request"><h2>Request and scope</h2>' + request + '</section>')
    out += ['<section id="exhibits"><h2>Evidence examined</h2>', _option_fields(options, _INTAKE_KEYS), _exhibits(info, True),
            '<p class="small">The table lists the evidence items that the findings cite.</p></section>',
            '<section id="method"><h2>Method and limits</h2>',
            '<p>CONAN-F generates findings from evidence records. The stored run identifies the findings that the Lean 4 '
            'proof checker accepted. This report shows those results. It does not run the proof checker again.</p>',
            _option_fields(options, ('method_notes',)),
            '<ul class="limits"><li>The findings state what the evidence records say. They do not identify the person '
            'who used a device or an account, or the reason.</li>'
            '<li>The proof check covers the step from records to findings. It does not check that the tools read the '
            'disk images correctly.</li>'
            '<li>This report is a summary. The stored run contains each finding, its source records and its proof. '
            'The verification command is <code>cop verify</code>.</li></ul>']
    store = case.get('facts_sha256')
    if isinstance(store, str) and store:
        out.append('<p class="small">Evidence store hash (SHA-256): <span class="mono">' + _h(store) + '</span></p>')
    out.append('</section>')
    return out


def _front(info, tz, case, findings, options, story, short=False):
    """What the records show, the days it happened on, then evidence examined and method."""
    counts, where = info['counts'], info['zone']
    clock_name = where['name'] + ' local time' if tz is not None else 'UTC'
    out = ['<section id="summary"><h2>Executive summary</h2>']
    if story['points']:
        out.append('<div class="keys">')
        for point in story['points']:
            body = '<p>' + ' '.join(_h(sentence) for sentence in point['sentences']) + '</p>'
            if point['key'] == 'devices' and story['devices']:
                body += _table(('Item', 'Device', 'Serial number', 'Volume label', 'First connection', 'Last connection'),
                               [tuple(_h(row[key]) or '—' for key in ('item', 'device', 'serial', 'label', 'first', 'last'))
                                for row in story['devices'][:6]], 'devices')
                if len(story['devices']) > 6:
                    body += '<p class="small">The table shows 6 of ' + f"{len(story['devices']):,}" + ' devices.</p>'
            out.append('<div class="key"><h3>' + _h(point['title']) + '</h3><div>' + body + '</div></div>')
        out.append('</div>')
    else:
        out.append('<p>The findings in this report cite no record of a type that the summary describes.</p>')
    days = info['days'][:7]
    if days:
        rows = []
        for day in days:
            events = ' · '.join(_h((group['one'] if group['count'] == 1 else f"{group['count']:,} {group['many']}")
                                   + ' (' + _span(group['first'], group['last'], tz) + ')') for group in _day_events(day['events']))
            rows.append((_h(_day(day['date'])), events or 'No key events on this day.'))
        out += ['<h3>Timeline</h3>', _table(('Day', 'Recorded events and times'), rows, 'days')]
    notes = ['Each statement is a count or a value from the evidence records that the '
             + _plural(counts['findings'], 'finding cites', 'findings cite') + '.', 'Times are in ' + _h(clock_name) + '.']
    if counts['likely']:
        notes.append(_plural(counts['likely'], 'finding uses', 'findings use') + ' a stated heuristic rule. The finding identifies this rule.')
    if counts['findings'] != counts['recorded']:
        notes.append(f"This report contains {counts['findings']:,} of the {counts['recorded']:,} findings in the stored run.")
    out.append('<p class="small">' + ' '.join(notes) + '</p>')
    if short:
        return out + ['</section>'] + _short_back(info, case, options)
    out.append('</section><section id="request"><h2>Request and scope</h2>')
    request = _option_fields(options, _REQUEST_KEYS)
    out.append(request or '<p>The report contains no request details from the author.</p>')
    out.append('</section><section id="exhibits"><h2>Evidence examined</h2>')
    intake = _option_fields(options, _INTAKE_KEYS)
    if intake:
        out.append(intake)
    out.append(_exhibits(info))
    out.append('<p class="small">The table lists evidence items that the findings cite. '
               'It includes the identifiers and stored hash values in the records. '
               'The Other submitted items field lists any additional items that the report author supplies.'
               + (' ' + _plural(info['unlabelled'], 'record has', 'records have') + ' no evidence item label.'
                  if info['unlabelled'] else '') + '</p></section>')
    checker = info['checker']
    tally = lambda rows: _h(', '.join(f"{row['name']} ({row['count']:,})" for row in rows)) or 'Not supplied'
    out += ['<section id="method"><h2>Examination methods</h2>',
            '<p>CONAN-F generates findings from evidence records. Each finding contains a statement, source references, and a proof.</p>',
            '<p>The stored run identifies the findings that the Lean 4 proof checker accepted. '
            'This report shows those results. It does not run the proof checker again.</p>',
            _option_fields(options, ('method_notes',)),
            '<h3>Tools and source records</h3>']
    named = [(_h(row['name']), 'Tool', f"{row['count']:,}") for row in info['tools']]
    named += [(_h(row['name']), 'Record reader', f"{row['count']:,}") for row in info['readers']]
    if named:
        out.append(_table(('Tool or reader as recorded', 'Function', 'Cited records'), named))
    else:
        out.append('<p>The cited records contain no tool names.</p>')
    out.append('<p class="small">Tool names include versions only when the source records supply them.</p>')
    out.append('<h3>Time reference</h3>')
    if tz is not None:
        out.append('<p>The tables use ' + _h(where['name']) + ' local time. '
                   'Each detailed timestamp includes its offset and Coordinated Universal Time (UTC). '
                   'Exact source statements keep their original times.</p>')
    else:
        out.append('<p>The tables use Coordinated Universal Time (UTC). '
                   + ('The records name ' + _h(where['name']) + '. This system could not convert that time zone.'
                      if where else 'The cited records contain no local time zone.') + '</p>')
    out.append('<p>Timeline dates do not include examination times or timestamps with an unknown meaning. '
               'Each detailed record keeps its original timestamp and meaning.</p>')
    out.append('<h3>Verification method</h3><p>A strong finding follows from the cited records and the declared proof rules. '
               'A heuristic finding also uses a stated heuristic rule.</p>')
    out.append(_fields([('Proposer as recorded', tally(checker['proposers'])),
                        ('Trust tier as recorded', tally(checker['trust'])), ('Declared axioms', tally(checker['axioms']))]))
    store = case.get('facts_sha256')
    out.append('<p>Independent verification uses the stored proof and the original evidence store. '
               'The verification command is <code>cop verify</code>.</p>')
    if isinstance(store, str) and store:
        out.append('<p>Evidence store hash (SHA-256): <span class="mono">' + _h(store) + '</span>.</p>')
    out.append('</section>')
    return out


_GLOSSARY = (
    ('Evidence item (exhibit)', 'A device, image file, or other item with an evidence label.'),
    ('Evidence record', 'Data from a source, with its source reference and recorded properties.'),
    ('Finding', 'A statement that the stored run records as accepted by the proof checker.'),
    ('Heuristic rule', 'A rule that uses a stated assumption to support an interpretation.'),
    ('Proof checker', 'Lean 4, the software that does a check of a formal proof against its declared rules and assumptions.'),
    ('Hash value', 'A value calculated from data. A comparison of hash values can detect a change in the data.'),
    ('MD5 / SHA-1 / SHA-256', 'Hash algorithms: Message-Digest Algorithm 5, Secure Hash Algorithm 1, and Secure Hash Algorithm 256-bit.'),
    ('UTC', 'Coordinated Universal Time, the reference for local time offsets.'),
    ('Provenance', 'The recorded source of data and the method used to obtain the data.'),
    ('Certificate', 'The statement, cited records, and formal proof for a finding.'),
    ('Trust tier / axiom', 'The recorded verification basis and an assumption that a proof can use.'),
    ('USB / URL / SID', 'Universal Serial Bus, Uniform Resource Locator, and security identifier.'),
)


def _option_fields(options, keys):
    return _fields([(label, _h(options[key])) for key, label in COVER if key in keys and options.get(key)]) if any(
        options.get(key) for key in keys) else ''


def _close(options, short=False):
    """Disposition and report authorization close the main report."""
    out = []
    if options.get('disposition') or not short:
        out.append('<section id="disposition"><h2>Evidence disposition</h2>'
                   + ('<p>' + _h(options['disposition']) + '</p>' if options.get('disposition') else
                      '<p>The report contains no disposition details for the original evidence or its copies.</p>')
                   + '</section>')
    out += ['<section id="signoff"><h2>Report authorization</h2><div class="sign">',
            '<div><span>Examiner</span><strong>' + _h(options.get('examiner') or '') + '</strong></div>',
            '<div><span>Report authorizer</span><strong>' + _h(options.get('authorizer') or '') + '</strong></div>',
            '<div><span>Date of report</span><strong>' + _h(options.get('report_date') or '') + '</strong></div></div>',
            '<div class="sign"><div><span>Signature</span><strong></strong></div></div>',
            '<p class="small">The report author supplies the administrative details and examination notes. '
            'The signature records authorization of this report.</p></section>']
    return out


def _glossary():
    return ('<section id="glossary"><h2>Terms and abbreviations</h2>'
            + _fields([(term, _h(meaning)) for term, meaning in _GLOSSARY]) + '</section>')


def _finding_title(finding):
    question = finding.get('question')
    if isinstance(question, str) and question.strip() and not re.fullmatch(
            r'(?:combined certified findings|certified findings|finding)', question.strip(), re.I):
        return question.strip()
    rows = [_object(row) for row in _rows(finding.get('cited_facts'))]
    kinds = list(dict.fromkeys(brief.KINDS.get(row.get('kind'), ('other', 'Source record'))[1]
                              for row in rows if isinstance(row.get('kind'), str)))
    return ' / '.join(kinds[:3]) or 'Examination result'


def _result_index(findings):
    """A source index, not a new claim or a model-written conclusion."""
    groups = {key: [] for key, _ in brief.LANES}
    seen = {key: set() for key in groups}   # a record cited by many findings is listed once
    for number, finding in findings:
        for row in _rows(finding.get('cited_facts')):
            row = _object(row)
            kind = row.get('kind')
            lane = brief.KINDS.get(kind, ('other',))[0] if isinstance(kind, str) else 'other'
            prov = _object(row.get('prov'))
            name = row.get('obj_text')
            if name is None:
                continue
            value = _h(name)
            if kind == 'systemSetting' and row.get('aux_text') is not None:
                value += ': ' + _h(row['aux_text'])
            item = prov.get('exhibit') or prov.get('image')
            if item:
                value += ' <span class="small">(' + _h(item) + ')</span>'
            key = json.dumps(row, ensure_ascii=False, sort_keys=True)
            if key not in seen[lane]:
                seen[lane].add(key)
                groups[lane].append((key, value, number, finding.get('finding_id', 'Finding')))
    rows = []
    for lane, label in brief.LANES:
        entries = groups[lane]
        if not entries:
            continue
        examples = '<br>'.join(value + f' · <a href="#finding-f{number}">' + _h(fid) + '</a>'
                              for _, value, number, fid in entries[:3])
        rows.append((_h(label), examples, f'{len(entries):,}'))
    return ('<h3>Results by topic</h3><p>The table identifies records that support the findings. '
            'It shows up to three source entries for each topic.</p>'
            + _table(('Topic', 'Source entries and finding references', 'Records'), rows)) if rows else ''


def _cited(rows, tz=None):
    """The cited records beside their finding, for reports without the full evidence appendix."""
    if not rows:
        return '<p>No copied evidence records supplied.</p>'
    table = []
    for raw in rows:
        row = _object(raw)
        prov = _object(row.get('prov'))
        source = ' · '.join(_h(prov[key]) for key in ('exhibit', 'image', 'artifact') if prov.get(key) is not None)
        properties = []
        for key, label in (('user', 'User'), ('sender_address', 'Sender'), ('recipient_address', 'Recipient'),
                           ('attachment_names', 'Attachments'), ('size', 'Size in bytes'), ('device', 'Device model'),
                           ('volume_label', 'Volume label'), ('filesystem', 'File system'), ('profile_path', 'Profile path'),
                           ('run_count', 'Recorded run count'), ('source', 'Source type'), ('recovered', 'Recovered entry')):
            if key in prov and prov[key] is not None:
                properties.append('<span class="small">' + label + ': ' + _h(prov[key]) + '</span>')
        related = '<br><span class="small">Related value: ' + _v(row, 'aux_text') + '</span>' if row.get('aux_text') is not None else ''
        table.append(('<strong>' + _v(row, 'id') + '</strong><br><span class="small">' + _v(row, 'kind') + '</span>',
                      _v(row, 'obj_text', '—') + related + ('<br>' + '<br>'.join(properties) if properties else ''),
                      _time(row, tz) + '<br><span class="small">Meaning: ' + _v(prov, 'time_meaning', 'not stated') + '</span>',
                      source or 'Unknown — not supplied'))
    return _table(('Record', 'Object', 'Recorded timestamp', 'Source'), table, 'cited')


def _activity(run):
    out = ['<section id="activity"><h2>Audit, coverage and claim history</h2>',
           '<p class="muted">These are supplied summaries, not independent checks. Missing measurements are unknown, '
           'not zero. Recorded activity and answer presence do not establish completeness or accuracy.</p>',
           '<h3>Audit integrity</h3>']
    audit = _object(run.get('audit'))
    if not audit:
        out.append('<p>Unknown — no audit summary was supplied.</p>')
    else:
        if audit.get('status') == 'invalid' or audit.get('passed') is False:
            out.append('<p class="notice warning">Invalid audit reported. Recorded events are diagnostic only.</p>')
        elif audit.get('status') == 'valid' and audit.get('passed') is True:
            out.append('<p>The bundle reports a passed audit integrity check. This renderer does not recheck the log.</p>')
        else:
            out.append('<p>Audit integrity is unknown or not established by this bundle.</p>')
        out.append(_fields([(label, _v(audit, key)) for label, key in (
            ('Declared status', 'status'), ('Recorded events', 'count'), ('File SHA-256', 'sha256'),
            ('Chain head', 'head'), ('External expected head', 'expected_head'))]))
        out.append(_details('Complete supplied audit summary', audit))
    out.append('<p class="small">Audit integrity does not establish authorship or complete history. '
               'Detecting a complete rewrite requires an independently retained checkpoint.</p><h3>Recorded coverage</h3>')
    coverage = _object(run.get('coverage'))
    if coverage.get('schema_version') == 1:
        rows = []
        for name, field, label in (('extraction', 'record_count', 'Extracted records'),
                                  ('inspection', 'record_count', 'Records returned by the fact tool'),
                                  ('citations', 'record_count', 'Distinct cited records'),
                                  ('certification', 'finding_count', 'Findings recorded as accepted')):
            section = _object(coverage.get(name))
            count = (_v(section, field) if section.get('status') == 'measured'
                     else 'Invalid' if section.get('status') == 'invalid' else 'Unknown — unmeasured')
            rows.append([_h(label), count, _v(section, 'status')])
        out.append(_table(['Measure', 'Count', 'Supplied status'], rows))
        questions = _object(coverage.get('questions'))
        out.append('<h4>Public question answer presence</h4>')
        out.append(_fields([(label, _v(questions, key) if questions.get('status') == 'measured'
                             else 'Unknown — not established') for label, key in (
            ('Answered', 'answered_count'), ('Unknown answers', 'unknown_count'),
            ('Unanswered', 'unanswered_count'), ('Missing responses', 'missing_count'))]))
        out.append('<p class="small">Inspection does not include SQL aggregates or prove that a model understood '
                   'a record. Accepted counts use recorded status, not certificate replay.</p>')
        out.append(_details('Complete supplied coverage, failures and limitations', coverage))
    else:
        out.append('<p>Unknown — coverage summary is absent or its schema is unsupported.</p>')
        if coverage:
            out.append(_details('Uninterpreted coverage summary', coverage))
    out.append('<h3>Recorded claim attempts</h3>')
    history = _object(run.get('history'))
    if history.get('schema_version') == 1:
        integrity = _object(history.get('audit_integrity')).get('status')
        if integrity == 'failed':
            out.append('<p class="notice warning">Invalid history audit reported. These events are diagnostic only.</p>')
        out.append('<p>Outcomes are recorded checker results. No revision or successful repair is inferred from '
                   'similar claims. Interrupted calls may be absent; missing timestamps are not reconstructed.</p>')
        if history.get('available') is not True:
            out.append('<p>History availability is unknown; this does not establish that no attempts occurred.</p>')
        for key, label in (('attempts', 'Recorded sequence'), ('unmatched_proposals', 'Proposals with unknown placement')):
            attempts = _rows(history.get(key))
            if attempts:
                out.append('<h4>' + label + '</h4>')
                out.append(_table(['Attempt / finding', 'Outcome', 'Started / completed', 'Explicit revision'], [
                    [_v(a, 'attempt_id') + '<br>' + _v(a, 'finding_id'),
                     _v(a, 'status') + ('; duplicate of ' + _v(a, 'duplicate_of') + ' (no new proof)'
                                        if a.get('duplicate_of') is not None else ''),
                     _v(a, 'started_at') + '<br>' + _v(a, 'completed_at'),
                     'revises ' + _v(a, 'revises') + '; link status ' + _v(a, 'revision_status')
                     if a.get('revises') is not None else 'None recorded']
                    for a in map(_object, attempts)]))
        out.append(_details('Complete supplied history and limitations', history))
    else:
        out.append('<p>Unknown — claim history is absent or its schema is unsupported.</p>')
        if history:
            out.append(_details('Uninterpreted history summary', history))
    return ''.join(out) + '</section>'


def _workflow(run, findings):
    """Keep agent work notes, bound certificate sentences, and review diagnostics apart."""
    out = []
    by_id, duplicates = {}, set()
    for number, finding in findings:
        fid = finding.get('finding_id')
        if not isinstance(fid, str):
            continue
        if fid in by_id:
            duplicates.add(fid)
        by_id[fid] = (number, finding)
    eligible = {fid: item for fid, item in by_id.items() if fid not in duplicates
                and isinstance(item[1].get('english'), str) and item[1]['english']}

    if 'collection' in run:
        receipt = _object(run['collection'])
        out.append('<section id="collection"><h2>New evidence available</h2>')
        if receipt.get('status') in ('completed', 'completed_with_limitations') and receipt.get('continuation_required') is True:
            out.append('<p class="notice warning">A separate evidence snapshot was collected. It is not incorporated '
                       'into the current findings. Continue in a new run, query the new records and issue new proofs; '
                       'old fact IDs and certificates cannot be carried over as current proof.</p>')
            out.append(_fields([(label, _v(receipt, key)) for label, key in (
                ('Collection status', 'status'), ('Snapshot ID', 'snapshot_id'), ('Facts path — literal text', 'facts'),
                ('Facts SHA-256', 'facts_sha256'), ('Intake configuration path — literal text', 'config'),
                ('Extraction health path — literal text', 'health'))]))
            if receipt.get('note'):
                out.append('<p class="small">' + _v(receipt, 'note') + '</p>')
        else:
            out.append('<p>A completed collection requiring continuation is not established by this receipt.</p>'
                       + _details('Uninterpreted collection receipt', receipt))
        out.append('</section>')

    if 'investigation' in run:
        plan = _object(run['investigation'])
        out.append('<section id="investigation"><h2>Investigation plan — agent-reported work</h2>'
                   '<p class="notice">Work status, searched sources, unresolved questions and next actions are '
                   'agent-reported notes, not proof. “Reviewed” does not mean answered, accurate or complete.</p>')
        if plan.get('schema_version') != 1 or plan.get('status') == 'unavailable':
            out.append('<p>A supported investigation plan is unavailable.</p>' + _details('Supplied plan metadata', plan))
        else:
            out.append(_fields([('Plan revision', _v(plan, 'revision')), ('Case ID', _v(plan, 'case_id'))]))
            for number, raw in enumerate(_rows(plan.get('questions')), 1):
                question = _object(raw)
                out += [f'<article id="plan-q{number}"><h3>' + _v(question, 'id') + ' · ' + _v(question, 'prompt') + '</h3>',
                        _fields([(label, _v(question, key)) for label, key in (
                            ('Agent-reported work status', 'work_status'), ('Stated finding IDs', 'finding_ids'),
                            ('Reported searches', 'searched'), ('Unresolved notes', 'unresolved'), ('Proposed next actions', 'next_actions'))])]
                if 'previous_run_notes' in question:
                    out.append(_details('Previous-run notes — unverified; no current proof is inferred', question['previous_run_notes']))
                out.append('</article>')
            if plan.get('disclaimer'):
                out.append('<p class="small">' + _v(plan, 'disclaimer') + '</p>')
        out.append('</section>')

    if 'case_answers' in run:
        answers = _object(run['case_answers'])
        out.append('<section id="answers"><h2>Question-by-question findings</h2>'
                   '<p class="notice">Only exact sentences matching a unique current-run record marked verified '
                   'are shown as certificate statements. Question association is not proof of relevance, accuracy '
                   'or completeness. This renderer does not independently replay certificates.</p>')
        mismatch = (_object(run.get('case')).get('case_id') is not None and answers.get('case_id') is not None
                    and run['case']['case_id'] != answers['case_id'])
        if (answers.get('schema_version') != 1 or answers.get('kind') != 'certificate_sentence_answers'
                or answers.get('status') == 'unavailable' or mismatch):
            out.append('<p>Question answers are unavailable, unsupported, or not bound to this case.</p>'
                       + _details('Uninterpreted answer view — not certified', answers))
        else:
            for number, raw in enumerate(_rows(answers.get('questions')), 1):
                question = _object(raw)
                out += [f'<article id="answer-q{number}"><h3>' + _v(question, 'id') + ' · ' + _v(question, 'prompt') + '</h3>',
                        _fields([('Declared answer presence', _v(question, 'status')),
                                 ('Agent-reported work status', _v(question, 'work_status'))])]
                displayed = 0
                for raw_entry in _rows(question.get('certified_findings')):
                    entry = _object(raw_entry)
                    linked = eligible.get(entry.get('finding_id')) if isinstance(entry.get('finding_id'), str) else None
                    if linked and entry.get('sentence') == linked[1]['english']:
                        index, finding = linked
                        out += ['<p><span class="badge">Recorded certificate statement</span> '
                                + f'<a href="#finding-f{index}">' + _v(finding, 'finding_id') + '</a></p>',
                                '<p class="sentence">' + _h(finding['english']) + '</p>',
                                '<p class="small">Reported association: ' + _v(entry, 'association')
                                + '. This is not a proof that the question is answered.</p>']
                        displayed += 1
                    else:
                        out.append('<p class="notice warning">An answer entry has no matching unique current-run '
                                   'certificate sentence. It is unverified.</p>' + _details('Unbound answer entry', raw_entry))
                if not displayed:
                    out.append('<p>No bound certificate statement is available for this question. '
                               'This does not establish that no relevant evidence exists.</p>')
                out.append(_fields([(label, _v(question, key)) for label, key in (
                    ('Reported searches — unverified', 'searched'), ('Unresolved notes — unverified', 'unresolved'),
                    ('Proposed next actions — unverified', 'next_actions'))]))
                for key, label in (('refusals', 'Refused proposals and diagnostics — not certified'),
                                   ('issues', 'Question-association issues — not certified'),
                                   ('previous_run_notes', 'Previous-run notes — unverified')):
                    if question.get(key):
                        out.append(_details(label, question[key]))
                out.append('</article>')
            if answers.get('disclaimer'):
                out.append('<p class="small">' + _v(answers, 'disclaimer') + '</p>')
        out.append('</section>')

    if 'answer_projection' in run:
        from agent.answer_store import report_projection
        projection, problem = report_projection(run)
        out.append('<section id="structured-answers"><h2>Structured answers from claim fields</h2>'
                   '<p>Values come from explicit fields of the recorded claims. Question placement, relevance and '
                   'completeness are not proved. Independent certificate verification is separate.</p>')
        if problem:
            out.append('<p class="notice warning">The supplied structured answer view does not match its claim bindings: '
                       + _h(problem) + '</p>' + _details('Unverified supplied answer view', run['answer_projection']))
        else:
            for answer in projection['submission']['answers']:
                out.append('<article><h3>' + _v(answer, 'question_id') + '</h3>'
                           + _details('Structured answer — ' + answer['status'], answer))
                ids = list(dict.fromkeys(leaf['candidate_id'] for leaf in projection['leaves']
                                         if leaf['question_id'] == answer['question_id']))
                for fid in ids:
                    if fid in eligible:
                        out.append('<p>Claim ' + _h(fid) + ': <a href="#proof-f' + str(eligible[fid][0]) + '">proof record</a>.</p>')
                out.append('</article>')
            out.append(_details('Field links and omitted or conflicting bindings', {
                key: projection[key] for key in ('leaves', 'unsupported', 'dropped', 'conflicts')}))
        out.append('</section>')

    if 'conflicts' in run:
        review = _object(run['conflicts'])
        out.append('<section id="conflicts"><h2>Cross-record review — unverified diagnostics</h2>'
                   '<p class="notice warning">These are leads for review, not certified contradictions or a choice '
                   'of which source is true. Shared labels and repeated events can be legitimate. '
                   'No diagnostic does not mean no conflict exists.</p>')
        if review.get('schema_version') == 1 and review.get('status') == 'unavailable':
            out.append('<p class="notice warning">Conflict review unavailable: ' + _v(review, 'reason') + '</p>'
                       + _fields([('Recorded error type', _v(review, 'error_type'))]))
        elif review.get('schema_version') != 1 or review.get('status') != 'diagnostic':
            out.append('<p>A supported diagnostic review is unavailable.</p>' + _details('Uninterpreted review metadata', review))
        else:
            scope = _object(review.get('scope'))
            if scope.get('scan_truncated') is True or scope.get('diagnostics_truncated') is True:
                out.append('<p class="notice warning">REVIEW TRUNCATED: the scan or diagnostic output reached its limit. '
                           'Unshown records or diagnostics remain unreviewed here.</p>')
            out.append(_fields([(label, _v(scope, key)) for label, key in (
                ('Records examined', 'records_examined'), ('Maximum records', 'max_records'),
                ('Scan truncated', 'scan_truncated'), ('Diagnostic output truncated', 'diagnostics_truncated'), ('Input scope', 'input'))]))
            rows = _rows(review.get('diagnostics'))
            if not rows:
                out.append('<p>No matching diagnostics were recorded within the supplied review scope. '
                           'This is not a finding that the evidence is consistent.</p>')
            for number, raw in enumerate(rows, 1):
                diagnostic = _object(raw)
                if diagnostic.get('status') != 'diagnostic':
                    out.append(_details('Unrecognized review entry — not certified', raw))
                    continue
                out += [f'<article id="conflict-d{number}"><h3>' + _v(diagnostic, 'id') + ' · ' + _v(diagnostic, 'category') + '</h3>',
                        '<span class="badge">Unverified diagnostic</span><p>' + _v(diagnostic, 'summary') + '</p>',
                        '<p>' + _v(diagnostic, 'why') + '</p>',
                        _fields([('Witness record IDs — not certified citations', _v(diagnostic, 'record_ids')),
                                 ('Observed conditions', _v(diagnostic, 'observed')),
                                 ('Further review needed', _v(diagnostic, 'required'))]),
                        _details('Copied witness records and provenance — not certified findings', diagnostic.get('records')),
                        '</article>']
            if review.get('limitations'):
                out.append(_details('Review limitations', review['limitations']))
            if review.get('disclaimer'):
                out.append('<p class="small">' + _v(review, 'disclaimer') + '</p>')
        out.append('</section>')
    return ''.join(out)


def render_html(run: dict, options: dict | None = None) -> str:
    """Render literal bundle contents without certifying them or loading linked files."""
    if not isinstance(run, dict):
        raise TypeError('run must be a bundle object')
    options = options or {}
    case = _object(run.get('case'))
    findings = [(i, row) for i, row in enumerate(_rows(run.get('findings')), 1)
                if isinstance(row, dict) and row.get('status') == 'verified']
    recorded, chosen, sections = len(findings), options.get('ids'), options.get('sections')
    if chosen is not None:
        wanted = set(chosen)
        findings = [(i, row) for i, row in findings if row.get('finding_id') in wanted]
        if (len(findings) != len(wanted)
                or {row.get('finding_id') for _, row in findings} != wanted):
            raise ValueError('The selection names a finding that is not recorded exactly once as verified.')
    # The plan cross-references every finding, so it only belongs in a report that has them all.
    left_out = [name for name in SECTIONS if (sections is not None and name not in sections)
                or (name == 'workflow' and chosen is not None)]
    show = lambda name: name not in left_out
    short = bool(options.get('brief'))   # summary, evidence, limits and sign-off only: one or two printed pages
    unverified = [row for row in _rows(run.get('findings'))
                  if not isinstance(row, dict) or row.get('status') != 'verified']
    title = _v(case, 'name', 'Untitled investigation')
    info = brief.build(run, ids=chosen, days=31)
    tz = brief.clock(info['zone']['name']) if info['zone'] and info['zone']['known'] else None
    out = ['<!doctype html><html lang="en"><head><meta charset="utf-8">',
           '<meta name="viewport" content="width=device-width,initial-scale=1">',
           '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; '
           'img-src \'none\'; base-uri \'none\'; form-action \'none\'">',
           '<title>Report of digital forensic examination — ' + title + '</title><style>' + _CSS + '</style></head><body class="report">'
           + ('<main class="brief">' if short else '<main>'),
           '<header><div class="eyebrow">Report of digital forensic examination</div><h1>' + title + '</h1>']
    # Report identification precedes the summary. Request details have their own section.
    cover = [(label, _h(options[key])) for key, label in COVER if key in _HEADER_KEYS and options.get(key)]
    if cover:
        out.append(_fields(cover))
    out.append('<p class="small">Source run: ' + _v(case, 'generated_at') + '</p>')
    navigation = [('findings', 'Findings'), ('judgments', 'Conclusions'),
                  ('disposition', 'Disposition'), ('signoff', 'Authorization'), ('glossary', 'Terms'),
                  ('needs', 'Refused proposals'),
                  ('evidence', 'Evidence'), ('proofs', 'Proofs'), ('activity', 'Activity')]
    navigation = [(anchor, label) for anchor, label in navigation
                  if anchor in ('findings', 'glossary', 'signoff', 'disposition') or show(anchor)]
    if any(options.get(key) for key in _INCIDENT_KEYS):
        navigation.insert(2, ('incident', 'Incident response'))
    navigation = [('summary', 'Executive summary'), ('request', 'Request'), ('exhibits', 'Evidence examined'), ('method', 'Methods')] + navigation
    if short:   # a short report needs links only when optional parts make it long
        extra = [(anchor, label) for anchor, label in navigation if anchor in SECTIONS and show(anchor)]
        navigation = extra and [('summary', 'Executive summary'), ('exhibits', 'Evidence examined'),
                                ('method', 'Method and limits'), *extra, ('signoff', 'Authorization')]
    scope = []
    if chosen is not None:
        scope.append(f'<p class="notice warning"><strong>Selected findings only.</strong> This report shows {len(findings)} '
                     f'of the {recorded} entries recorded as verified, chosen by the person who produced it. '
                     'Entries left out are omitted, not refuted.</p>')
    if left_out and not short:
        scope.append('<p class="small">Left out of this report: '
                     + _h(', '.join(SECTION_LABELS[name] for name in left_out)) + '. The complete run bundle holds them.</p>')
    out += [''.join(scope) + '</header>',
            '<nav aria-label="Report sections">' + ''.join('<a href="#' + anchor + '">' + label + '</a>'
                                                          for anchor, label in navigation) + '</nav>' if navigation else '',
            *_front(info, tz, case, findings, options, narrative.build(run, ids=chosen), short)]
    if not short:
        out += ['<section id="findings"><h2>Examination findings</h2>',
                '<p>Each finding identifies its source records. Open the exact statement to read the original certificate text. '
                'The report keeps that text unchanged.</p>', _result_index(findings)]
    if not findings:
        out.append('<p>No entries marked verified were supplied. This does not establish that no relevant evidence exists.</p>')
    for number, finding in ([] if short else findings):
        out += [f'<article id="finding-f{number}"><h3>' + _v(finding, 'finding_id') + ' · ' + _h(_finding_title(finding)) + '</h3>',
                '<span class="badge">' + _v(finding, 'strength') + '</span><span class="badge">Recorded as verified</span>',
                '<details class="exact-statement"><summary>Exact certificate statement</summary>',
                '<p class="sentence">' + _v(finding, 'english') + '</p>',
                '<p class="small">Rules: ' + _v(finding, 'rules') + '</p></details>']
        rows = _rows(finding.get('cited_facts'))
        links = [f'<a href="#evidence-f{number}-r{index}">Fact ' + _v(_object(row), 'id') + '</a>'
                 for index, row in enumerate(rows, 1)]
        pointers = []
        out.append(_cited(rows, tz))
        if show('evidence'):
            pointers.append(', '.join(links) if links else 'No copied evidence records supplied.')
        if show('proofs'):
            pointers.append(f'<a href="#proof-f{number}">Proof record</a>')
        else:
            out.append('<p class="small">Certificate: trust tier ' + _v(finding, 'trust_tier') + '. Declared axioms: '
                       + _v(finding, 'axioms') + '. The Lean source is in the run bundle.</p>')
        out.append(('<p>' + ' · '.join(pointers) + '</p>' if pointers else '') + '</article>')
    if unverified and not short:
        out += ['<p class="notice warning">Some entries in the findings list are not marked verified. '
                'They are not displayed as certified findings.</p>', _details('Unverified or malformed finding entries', unverified)]
    if not short:
        out.append('</section>')
    refusal_start = len(out)
    if show('needs'):
        out.append('<section id="needs"><h2>Not established / further evidence needed</h2>'
                   '<p class="muted">Refused proposals and their diagnostics are not certified findings. Refusal alone does not '
                   'prove a claim false. Suggested evidence may not exist or make the claim provable.</p>')
        rejections = _rows(run.get('rejections'))
        if not rejections:
            out.append('<p>No refusal details were supplied. This is not a claim that all proposals succeeded.</p>')
        for number, raw in enumerate(rejections, 1):
            row = _object(raw)
            out += [f'<article id="rejection-r{number}"><h3>' + _v(row, 'finding_id') + '</h3>',
                    '<span class="badge">Not certified</span><p>' + _v(row, 'reason') + '</p>']
            gap = _object(row.get('proof_gap'))
            if gap.get('status') == 'diagnostic':
                out.append('<p>' + _v(gap, 'summary') + '</p>')
                for requirement in map(_object, _rows(gap.get('requirements'))):
                    out += ['<h4>' + _v(requirement, 'category') + '</h4><p>' + _v(requirement, 'reason') + '</p>',
                            '<p><strong>Further evidence or action:</strong> ' + _v(requirement, 'action') + '</p>',
                            _fields([(label, _v(requirement, key)) for label, key in (
                                ('Proposed fact IDs (not evidence links)', 'fact_ids'), ('Observed', 'observed'), ('Required condition', 'required'))])]
                out.append('<p class="small">' + _v(gap, 'disclaimer') + '</p>')
            else:
                out.append('<p>Further-evidence requirements are unknown; no recognized diagnostic was supplied.</p>')
            out.append(_details('Supplied rejected proposal', raw) + '</article>')
        out.append('</section>')
    refusals = out[refusal_start:]
    del out[refusal_start:]
    if show('judgments'):
        out.append('<section id="judgments"><h2>Analysis and conclusions</h2>'
                   '<p class="muted">These are unverified inferences. Citing certified findings does not certify a conclusion, '
                   'intent, causation or device attribution.</p>')
        conclusions = _rows(run.get('conclusions'))
        if not conclusions:
            out.append('<p>No investigator judgments were supplied.</p>')
        for raw in conclusions:
            row = _object(raw)
            out.append('<article><h3>' + _v(row, 'conclusion_id') + '</h3><span class="badge">Unverified judgment</span>'
                       '<p class="sentence">' + _v(row, 'text') + '</p>'
                       + _fields([('Stated supporting finding IDs', _v(row, 'finding_ids'))])
                       + _details('Supplied judgment record', raw) + '</article>')
        out.append('</section>')
    if any(options.get(key) for key in _INCIDENT_KEYS):
        out.append('<section id="incident"><h2>Incident response</h2>'
                   '<p>The report author supplies the following incident assessment and actions.</p>'
                   + _option_fields(options, _INCIDENT_KEYS) + '</section>')
    out += _close(options, short)
    out.append('<div class="appendices">')
    if not short:
        out.append(_glossary())
    out.extend(refusals)
    if show('workflow'):
        out.append(_workflow(run, findings))
    if show('evidence'):
        out.append('<section id="evidence"><h2>Evidence records</h2>'
                   '<p class="muted">Every copied citation is shown in its finding’s scope. Provenance is supplied metadata, '
                   'not proof that a parser or its interpretation is correct. Source locations appear only when supplied.</p>')
        copies = {}
        for _, finding in findings:
            for row in _rows(finding.get('cited_facts')):
                if isinstance(row, dict):
                    identity = json.dumps(row.get('id'), sort_keys=True)
                    copies.setdefault(identity, set()).add(json.dumps(row, sort_keys=True, ensure_ascii=False))
        for number, finding in findings:
            for index, raw in enumerate(_rows(finding.get('cited_facts')), 1):
                row = _object(raw)
                prov = _object(row.get('prov'))
                out.append(f'<article id="evidence-f{number}-r{index}"><h3>Fact ' + _v(row, 'id')
                           + ' · finding ' + _v(finding, 'finding_id') + '</h3>')
                if len(copies.get(json.dumps(row.get('id'), sort_keys=True), ())) > 1:
                    out.append('<p class="notice warning">Conflicting copied rows share this fact ID. '
                               'They remain separate; this renderer does not resolve the conflict.</p>')
                if not isinstance(raw, dict):
                    out.append('<p class="notice warning">Malformed copied record — no source binding established.</p>')
                out.append(_fields([(label, _v(source, key)) for label, source, key in (
                    ('Kind', row, 'kind'), ('Image', prov, 'image'), ('Exhibit', prov, 'exhibit'),
                    ('Artifact', prov, 'artifact'), ('Object', row, 'obj_text'), ('Object entity ID', row, 'obj'),
                    ('Related value', row, 'aux_text'), ('Related entity ID', row, 'aux'),
                    ('Timestamp meaning', prov, 'time_meaning'), ('Uncertainty (microseconds)', row, 'res'),
                    ('Parser', prov, 'parser'), ('Tool', prov, 'tool'), ('Row SHA-256', row, 'row_sha256'))]
                    + [('Recorded timestamp', _time(row, tz))]))
                out += ['<h4>Full copied provenance</h4>', _pre(row['prov']) if 'prov' in row else '<p>Unknown — not supplied.</p>',
                        _details('Complete copied record', raw), f'<p class="small"><a href="#finding-f{number}">Back to finding</a></p></article>']
        out.append('</section>')
    if show('proofs'):
        out.append('<section id="proofs"><h2>Proof records</h2><p class="muted">Declared claims and embedded Lean '
                   'are copied from the bundle. Source code is displayed as text, never executed. No filesystem links are inferred.</p>')
        for number, finding in findings:
            out += [f'<article id="proof-f{number}"><h3>Proof for ' + _v(finding, 'finding_id') + '</h3>',
                    _fields([('Trust tier', _v(finding, 'trust_tier')), ('Declared axioms', _v(finding, 'axioms'))]),
                    '<h4>Declared claim</h4>', _pre(finding['claim']) if 'claim' in finding else '<p>Unknown — not supplied.</p>']
            lean = finding.get('lean')
            out.append('<h4>Embedded Lean source</h4>' + (_pre(lean, source=True) if isinstance(lean, str) and lean.strip()
                       else '<p>Unknown — embedded Lean source was not included. No file is loaded by this renderer.</p>'))
            out.append(f'<p class="small"><a href="#finding-f{number}">Back to finding</a></p></article>')
        out.append('</section>')
    out += [_activity(run) if show('activity') else '',
            '<footer>CONAN-F · ' + ('' if short else 'Report rendering only. '
            'Certificate validity, source binding, audit integrity and forensic interpretation are distinct checks. ')
            + 'To print, use Print / Save as PDF in the browser.' + ('' if short else ' The report contains all displayed content.')
            + '</footer></div>', '</main></body></html>']
    main_number, appendix_number, in_appendix = 0, 0, False
    for i, block in enumerate(out):
        if block == '<div class="appendices">':
            in_appendix = True
        if '<section id=' in block:
            def numbered(match):
                nonlocal main_number, appendix_number
                if in_appendix:
                    appendix_number += 1
                    prefix = 'Appendix ' + chr(64 + appendix_number) + ' — '
                else:
                    main_number += 1
                    prefix = str(main_number) + '. '
                return match[1] + prefix + match[2] + '</h2>'
            out[i] = re.sub(r'(<section id="[^"]+"><h2>)([^<]+)</h2>', numbered, block)
    rendered = '\n'.join(out) + '\n'
    if left_out or short:   # links into sections this report leaves out become plain text
        present = set(re.findall(r' id="([^"]+)"', rendered))
        rendered = re.sub(r'<a href="#([^"]+)">(.*?)</a>',
                          lambda link: link.group(0) if link.group(1) in present else link.group(2), rendered)
    return rendered
