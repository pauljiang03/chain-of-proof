"""Standalone HTML for supplied investigation bundles; never verifies or reads files.

`render_html(run)` reproduces the whole bundle. `render_html(run, report_options(...))`
builds an examiner's report: chosen findings, chosen sections and cover details. A
report that leaves anything out says so on its first page.

Every report opens with who asked and why, a summary, the evidence items with their
identifiers and hash values, and the method and tools. Those pages are counts of the
bundle's own records (app/brief.py).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from html import escape
import json
import re

from . import brief

# Optional parts of a report. The certified findings themselves are always included.
SECTIONS = ('workflow', 'needs', 'judgments', 'evidence', 'proofs', 'activity')
SECTION_LABELS = {'workflow': 'question-by-question plan', 'needs': 'refused proposals',
                  'judgments': 'investigator judgments', 'evidence': 'full evidence records',
                  'proofs': 'Lean proof records', 'activity': 'audit, coverage and history'}
COVER = (('reference', 'Case reference'), ('requested_by', 'Requested by'), ('authority', 'Authority for the request'),
         ('purpose', 'Purpose and scope'), ('received', 'Evidence received'), ('examiner', 'Examiner'),
         ('organisation', 'Organisation'), ('report_date', 'Date of report'))
COVER_LIMITS = {'purpose': 600}   # characters; every other cover detail is at most 200
MAX_SELECTED = 2000
_FINDING_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}')


def report_options(ids=None, sections=None, reference='', examiner='', organisation='', **more):
    """Validate what goes into a report. `None` for ids or sections means everything."""
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
    options = {'ids': ids, 'sections': sections}
    given = {'reference': reference, 'examiner': examiner, 'organisation': organisation, **more}
    if set(given) - {key for key, _ in COVER}:
        raise ValueError('Unknown cover detail.')
    for key, _ in COVER:
        value = given.get(key, '')
        if (not isinstance(value, str) or len(value) > COVER_LIMITS.get(key, 200)
                or any(ord(c) < 32 or ord(c) == 127 for c in value)):
            raise ValueError('Cover details must be plain text of at most 200 characters (600 for the purpose and scope).')
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
.mono { font:12px/1.5 ui-monospace,SFMono-Regular,Consolas,monospace; overflow-wrap:anywhere; }
.days th:first-child, .days td:first-child { white-space:nowrap; overflow-wrap:normal; }
.days td:last-child, .exhibits td:last-child { white-space:nowrap; overflow-wrap:normal; }
.exhibits th, .days th, .exhibits td:first-child, .exhibits td:nth-child(2) { white-space:nowrap; overflow-wrap:normal; }
.exhibits td:last-child { white-space:normal; }
ol { padding-left:22px; } ol li { margin:6px 0; }
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
  summary { display:none; } a { color:inherit; } .notice { break-inside:avoid; }
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


def _front(info, tz, case, metrics=''):
    """Summary, evidence examined and method before the detailed findings."""
    counts, where = info['counts'], info['zone']
    clock_name = where['name'] + ' local time' if tz is not None else 'UTC'
    lead = '<strong>' + _plural(counts['findings'], 'finding', 'findings') + '</strong> in this report passed the proof checker'
    if counts['findings']:
        lead += (f": {counts['firm']:,} follow from the records alone and {counts['likely']:,} rest on a stated rule of thumb"
                 if counts['likely'] else ', each following from the records alone')
    lead += ('. They cite ' + _plural(counts['records'], 'evidence record', 'evidence records') + ' from '
             + _plural(len([item for item in info['exhibits'] if item['records']]), 'exhibit', 'exhibits') + '. '
             + (_plural(counts['refused'], 'proposed finding was', 'proposed findings were') + ' refused by the checker'
                if counts['refused'] else 'No proposed finding was refused') + ' in the stored run.')
    out = ['<section id="summary"><h2>Summary</h2><p class="lead">' + lead + '</p>',
           metrics]
    if counts['findings'] != counts['recorded']:
        out.append(f"<p>The stored run records {counts['recorded']:,} verified findings; the counts in this summary cover "
                   'only the ones selected for this report.</p>')
    if info['range']:
        first, last = brief.moment(info['range']['from'], tz), brief.moment(info['range']['to'], tz)
        busy = info['busiest']
        start, end = brief.moment(busy['from'], tz), brief.moment(busy['to'], tz)
        if None not in (first, last, start, end):
            out.append(f"<p>{counts['dated']:,} of the cited records carry the time of an event, from {first:%Y-%m-%d} to "
                       f"{last:%Y-%m-%d}. The busiest period runs from {start:%Y-%m-%d} to {end:%Y-%m-%d} and holds "
                       f"{busy['records']:,} of them. Times are in {_h(clock_name)}.</p>")
    if info['days']:
        rows = []
        for day in info['days']:
            events = ' · '.join(_h((group['one'] if group['count'] == 1 else f"{group['count']:,} {group['many']}")
                                   + ' (' + _span(group['first'], group['last'], tz) + ')') for group in day['events'])
            rows.append((_h(_day(day['date'])), events or 'No key events on this day.', f"{day['records']:,}"))
        shown = ('the ' + str(len(info['days'])) + ' busiest of ' + str(info['days_total']) + ' days'
                 if info['days_total'] > len(info['days']) else 'each day') + ' of the busiest period'
        out += ['<h3>Key events by day</h3>', _table(('Day', 'Key events recorded', 'Dated records'), rows, 'days'),
                '<p class="small">Shown for ' + shown + '. Key events are counted by record type — a device connection, '
                'an e-mail, a deletion — and are not chosen by a model. A count is a count of evidence records, which can '
                'be more than the number of things that happened. Each record is under the finding that cites it.</p>']
    out.append('</section><section id="exhibits"><h2>Evidence examined</h2>')
    if info['exhibits']:
        rows = []
        for item in info['exhibits']:
            identity = [_h('Device ' + value) for value in item['devices'] if item['label'].lower() not in value.lower()]
            identity += [_h('Volume serial ' + value) for value in item['volumes']]
            identity += [_h(fact['label'] + ': ' + ', '.join(fact['values'])) for fact in item['system']]
            digests = ['<span class="mono">' + _h(digest['algorithm'] + ' ' + digest['value']) + '</span> <span class="small">(record '
                       + _h(digest['record']) + ')</span>' for digest in item['digests']]
            acquired = [_h('Time as recorded: ' + value) for value in item['acquired']]
            acquired += [_h('Imaging tool as recorded: ' + value) for value in item['tools']]
            rows.append(('<strong>' + _h(item['label']) + '</strong>', _h(', '.join(item['images'])) or '—',
                         '<br>'.join(identity) or '—', '<br>'.join(digests) or 'None among the cited records',
                         '<br>'.join(acquired) or '—',
                         f"{item['records']:,} in " + _plural(item['findings'], 'finding', 'findings')))
        out.append(_table(('Exhibit', 'Image file', 'Identifiers', 'Hash values stored with the image',
                           'Acquisition', 'Cited records'), rows, 'exhibits'))
    else:
        out.append('<p>The cited evidence records name no exhibit.</p>')
    out.append('<p class="small">This lists the exhibits named by evidence records that verified findings cite, with the '
               'identifiers and hash values that are themselves cited records. It is not a list of everything submitted: '
               'an item that produced no cited record does not appear.'
               + (' ' + _plural(info['unlabelled'], 'cited record names', 'cited records name') + ' no exhibit.'
                  if info['unlabelled'] else '') + '</p></section>')
    checker = info['checker']
    tally = lambda rows: _h('; '.join(f"{row['name']} ({row['count']:,})" for row in rows)) or 'not stated'
    out += ['<section id="method"><h2>Method, tools and times</h2><ol>',
            '<li>Tools read the image files into evidence records. Each record keeps the exhibit, image and artefact it was read from.</li>',
            '<li>Findings were proposed from those records. Proposer as recorded: ' + tally(checker['proposers']) + '.</li>',
            '<li>Each proposed finding was given to the Lean proof checker together with the records it cites. Only findings '
            'the checker accepted are reported as findings. Trust tier as recorded: ' + tally(checker['trust'])
            + '. Declared axioms: ' + tally(checker['axioms']) + '.</li>',
            '<li>Opinions of the investigator, where recorded, are printed apart and marked as not checked.</li></ol>']
    named = [(_h(row['name']), 'Tool', f"{row['count']:,}") for row in info['tools']]
    named += [(_h(row['name']), 'Record reader', f"{row['count']:,}") for row in info['readers']]
    if named:
        out.append(_table(('Named by the evidence records', 'As', 'Records naming it'), named))
    else:
        out.append('<p>The cited evidence records name no tool.</p>')
    if tz is not None:
        out.append('<p><strong>Times.</strong> ' + _plural(where['records'], 'cited record names', 'cited records name') + ' '
                   + _h(where['name']) + ' as the time zone local times were converted from. Tables in this report give that '
                   'local time first, with its offset, and then UTC. Finding sentences are reproduced verbatim and quote UTC.</p>')
    else:
        out.append('<p><strong>Times.</strong> All times in this report are in UTC'
                   + ('; the records name the time zone ' + _h(where['name']) + ', which this system could not convert.'
                      if where else ': the cited records do not name the time zone of the examined computer.') + '</p>')
    store = case.get('facts_sha256')
    out.append('<p><strong>Checking this report.</strong> The stored run holds every cited record and every proof. '
               'An independent party can re-run the checker on it with <code>cop verify</code> and the original evidence store'
               + ('. Evidence store SHA-256 as recorded: <span class="mono">' + _h(store) + '</span>' if isinstance(store, str) and store else '')
               + '.</p></section>')
    return out


_GLOSSARY = (
    ('Exhibit', 'An item submitted for examination, such as a computer or a USB stick, under the label the evidence records use.'),
    ('Evidence record', 'One fact a tool read from an image file, kept with the place it was read from.'),
    ('Finding', 'A statement the proof checker accepted because the evidence records it cites support it.'),
    ('Strong / heuristic', 'A strong finding follows from the records alone. A heuristic finding also relies on a stated rule of thumb.'),
    ('Refused', 'A proposed finding the checker did not accept. A refusal does not show the statement is false.'),
    ('Proof checker', 'Lean 4, a program that accepts a statement only when it is given a complete proof of it.'),
    ('Hash value (MD5, SHA-1)', 'A fingerprint computed from the contents of an image, used to show that a copy has not changed.'),
    ('UTC', 'Coordinated Universal Time, the reference clock that local times are offset from.'),
)


def _close(options):
    """A glossary and a place to sign, after the findings and before any appendix."""
    out = ['<section id="glossary"><h2>Terms used</h2><dl>']
    out += ['<dt>' + _h(term) + '</dt><dd>' + _h(meaning) + '</dd>' for term, meaning in _GLOSSARY]
    out += ['</dl></section><section id="signoff"><h2>Sign-off</h2><div class="sign">',
            '<div><span>Examiner</span><strong>' + _h(options.get('examiner') or '') + '</strong></div>',
            '<div><span>Signature</span><strong></strong></div>',
            '<div><span>Date of report</span><strong>' + _h(options.get('report_date') or '') + '</strong></div></div>',
            '<p class="small">Add any declaration your court or organisation requires; this report does not supply one. '
            'A name or date printed here was entered by the person who produced the report.</p></section>']
    return out


def _cited(rows, tz=None):
    """The cited records beside their finding, for reports without the full evidence appendix."""
    if not rows:
        return '<p>No copied evidence records supplied.</p>'
    table = []
    for raw in rows:
        row = _object(raw)
        prov = _object(row.get('prov'))
        source = ' · '.join(_h(prov[key]) for key in ('exhibit', 'image', 'artifact') if prov.get(key) is not None)
        related = '<br><span class="small">Related value: ' + _v(row, 'aux_text') + '</span>' if row.get('aux_text') is not None else ''
        table.append(('<strong>' + _v(row, 'id') + '</strong><br><span class="small">' + _v(row, 'kind') + '</span>',
                      _v(row, 'obj_text', '—') + related,
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
    case, stats = _object(run.get('case')), _object(run.get('stats'))
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
    unverified = [row for row in _rows(run.get('findings'))
                  if not isinstance(row, dict) or row.get('status') != 'verified']
    title = _v(case, 'name', 'Untitled investigation')
    info = brief.build(run, ids=chosen, days=31)
    tz = brief.clock(info['zone']['name']) if info['zone'] and info['zone']['known'] else None
    out = ['<!doctype html><html lang="en"><head><meta charset="utf-8">',
           '<meta name="viewport" content="width=device-width,initial-scale=1">',
           '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; '
           'img-src \'none\'; base-uri \'none\'; form-action \'none\'">',
           '<title>Investigation report — ' + title + '</title><style>' + _CSS + '</style></head><body><main>',
           '<header><div class="eyebrow">CONAN-F · Forensic examination report</div><h1>' + title + '</h1>']
    # The first page reads as an examiner's report does: who asked and why, then the summary.
    cover = [(label, _h(options[key])) for key, label in COVER if options.get(key)]
    if cover:
        out.append(_fields(cover) + '<p class="small">Entered by the person who produced this report. '
                   'These details are not part of the stored run and were not checked.</p>')
    out.append(_fields([('Run recorded', _v(case, 'generated_at')), ('Execution outcome', _v(case, 'ended'))]))
    metrics = ('<p class="small">Totals the stored run itself reports: ' + ', '.join(
        _v(stats, key, 'unknown') + ' ' + label for key, label in (
            ('verified', 'accepted'), ('rejected', 'refused'), ('proposals', 'proposed'))) + '.</p>')
    navigation = [('findings', 'Findings'), ('needs', 'Not established'), ('judgments', 'Judgments'),
                  ('glossary', 'Terms'), ('signoff', 'Sign-off'),
                  ('evidence', 'Evidence'), ('proofs', 'Proofs'), ('activity', 'Activity')]
    navigation = [(anchor, label) for anchor, label in navigation
                  if anchor in ('findings', 'glossary', 'signoff') or show(anchor)]
    if show('workflow'):
        navigation = [(anchor, label) for key, anchor, label in (
            ('collection', 'collection', 'New evidence'),
            ('investigation', 'investigation', 'Investigation plan'), ('case_answers', 'answers', 'Question answers'),
            ('answer_projection', 'structured-answers', 'Structured answers'),
            ('conflicts', 'conflicts', 'Cross-record review')) if key in run] + navigation
    navigation = [('summary', 'Summary'), ('exhibits', 'Evidence examined'), ('method', 'Method')] + navigation
    scope = []
    if chosen is not None:
        scope.append(f'<p class="notice warning"><strong>Selected findings only.</strong> This report shows {len(findings)} '
                     f'of the {recorded} entries recorded as verified, chosen by the person who produced it. '
                     'Entries left out are omitted, not refuted.</p>')
    if left_out:
        scope.append('<p class="small">Left out of this report: '
                     + _h('; '.join(SECTION_LABELS[name] for name in left_out)) + '. The complete run bundle holds them.</p>')
    out += [''.join(scope) + '</header>',
            '<nav aria-label="Report sections">' + ''.join('<a href="#' + anchor + '">' + label + '</a>'
                                                          for anchor, label in navigation) + '</nav>',
            *_front(info, tz, case, metrics),
            _workflow(run, findings) if show('workflow') else '',
            '<section id="findings"><h2>Recorded certified findings</h2>',
            '<p class="muted">Sentences are reproduced verbatim. “Strong” describes what the records support; '
            '“heuristic” relies on a stated rule of thumb. These labels do not prove parser correctness or real-world completeness.</p>']
    if not findings:
        out.append('<p>No entries marked verified were supplied. This does not establish that no relevant evidence exists.</p>')
    for number, finding in findings:
        out += [f'<article id="finding-f{number}"><h3>' + _v(finding, 'finding_id') + '</h3>',
                '<span class="badge">' + _v(finding, 'strength') + '</span><span class="badge">Recorded as verified</span>',
                '<p class="small">Question: ' + _v(finding, 'question') + '</p>',
                '<p class="sentence">' + _v(finding, 'english') + '</p>',
                '<p class="small">Rules: ' + _v(finding, 'rules') + '</p>']
        rows = _rows(finding.get('cited_facts'))
        links = [f'<a href="#evidence-f{number}-r{index}">Fact ' + _v(_object(row), 'id') + '</a>'
                 for index, row in enumerate(rows, 1)]
        pointers = []
        if show('evidence'):
            pointers.append(', '.join(links) if links else 'No copied evidence records supplied.')
        else:
            out.append(_cited(rows, tz))
        if show('proofs'):
            pointers.append(f'<a href="#proof-f{number}">Proof record</a>')
        else:
            out.append('<p class="small">Certificate: trust tier ' + _v(finding, 'trust_tier') + '; declared axioms '
                       + _v(finding, 'axioms') + '. The Lean source is in the run bundle.</p>')
        out.append(('<p>' + ' · '.join(pointers) + '</p>' if pointers else '') + '</article>')
    if unverified:
        out += ['<p class="notice warning">Some entries in the findings list are not marked verified. '
                'They are not displayed as certified findings.</p>', _details('Unverified or malformed finding entries', unverified)]
    out.append('</section>')
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
    if show('judgments'):
        out.append('<section id="judgments"><h2>Investigator judgments — outside Lean</h2>'
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
    out += _close(options)
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
    out += [_activity(run) if show('activity') else '', '<footer>CONAN-F · Report rendering only. '
            'Certificate validity, source binding, audit integrity and forensic interpretation are distinct checks. '
            'To print, use your browser’s Print / Save as PDF; all content is embedded and nothing is loaded from elsewhere.</footer>',
            '</main></body></html>']
    rendered = '\n'.join(out) + '\n'
    if left_out:   # links into sections this report leaves out become plain text
        present = set(re.findall(r' id="([^"]+)"', rendered))
        rendered = re.sub(r'<a href="#([^"]+)">(.*?)</a>',
                          lambda link: link.group(0) if link.group(1) in present else link.group(2), rendered)
    return rendered
