"""Standalone report safety and fidelity, using synthetic bundles only."""
import copy
import html
from html.parser import HTMLParser
import json
import re
import unittest
from unittest.mock import patch

from app.report import SECTIONS, render_html, report_options


def record(number=7, **updates):
    row = {'id': number, 'kind': 'fileSeen', 't': 1_700_000_000_123_456, 'res': 2_000_000,
           'obj': 1, 'obj_text': r'C:\Files\report.txt', 'aux': 2, 'aux_text': 'VOL-A',
           'row_sha256': 'a' * 64, 'prov': {'image': 'synthetic.E01', 'exhibit': 'TEST',
           'artifact': 'test artifact', 'offset': 4096, 'time_meaning': 'record observation',
           'parser': 'synthetic parser', 'tool': 'synthetic tool', 'nested': {'page': 4}}}
    row.update(updates)
    return row


def finding(**updates):
    row = {'finding_id': 'F1', 'status': 'verified', 'question': 'What was recorded?',
           'english': 'A record names <example> & a path.\nNo copy is inferred.',
           'strength': 'strong', 'rules': ['R1'], 'cited_facts': [record()],
           'claim': {'fileRecorded': [7]}, 'trust_tier': 'kernel', 'axioms': [],
           'lean': '-- synthetic rendering fixture\nexample : True := by trivial\n'}
    row.update(updates)
    return row


def bundle(*findings):
    return {'version': 1, 'case': {'name': 'Synthetic investigation', 'generated_at': '2026-11-14T12:00:00Z'},
            'stats': {'verified': len(findings), 'rejected': 0, 'proposals': len(findings)},
            'findings': list(findings), 'rejections': [], 'conclusions': []}


class Markup(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.tags, self.ids, self.links, self.sentences = [], [], [], []
        self.current_sentence = None
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append((tag, attrs))
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if 'href' in attrs:
            self.links.append(attrs['href'])
        if tag == 'p' and attrs.get('class') == 'sentence':
            self.current_sentence = []

    def handle_endtag(self, tag):
        if tag == 'p' and self.current_sentence is not None:
            self.sentences.append(''.join(self.current_sentence))
            self.current_sentence = None

    def handle_data(self, data):
        if self.current_sentence is not None:
            self.current_sentence.append(data)


class AppReport(unittest.TestCase):
    def test_professional_fields_and_optional_incident_assessment_stay_author_supplied(self):
        data = bundle(finding())
        options = report_options(sections=[], report_id='R-9 <x>', report_version='2',
                                 address='Lab address', request_date='2026-11-01',
                                 collection_method='Encrypted delivery', additional_items='E2: not examined',
                                 method_notes='Procedure A. Reader version 2.', disposition='E1 retained by Lab.',
                                 authorizer='Reviewer', impact='Service interrupted.', root_cause='See F1.',
                                 response='Host isolated.', recommendations='Review access. Owner: IT.')
        rendered = render_html(data, options)
        self.assertIn('R-9 &lt;x&gt;', rendered)
        for text in ('Encrypted delivery', 'E2: not examined', 'Procedure A. Reader version 2.',
                     'E1 retained by Lab.', 'Host isolated.', 'Review access. Owner: IT.'):
            self.assertIn(text, rendered)
        self.assertIn('The report author supplies the following incident assessment and actions.', rendered)
        self.assertNotIn('id="incident"', render_html(data))
        self.assertNotIn('id="limits"', rendered)
        self.assertLess(rendered.index('id="signoff"'), rendered.index('id="glossary"'))
        headings = re.findall(r'<section id="[^"]+"><h2>(.*?)</h2>', rendered)
        numbered = [text for text in headings if not text.startswith('Appendix')]
        self.assertEqual([int(text.split('.')[0]) for text in numbered], list(range(1, len(numbered) + 1)))
        self.assertIn('Appendix A — Terms and abbreviations', headings)

    def test_result_index_and_properties_keep_source_scope_and_exact_statements(self):
        first = record(prov={'exhibit': 'E1', 'size': 0, 'recovered': False, 'user': '<u>'})
        second = record(prov={'exhibit': 'E2', 'size': 20, 'user': 'B'})
        data = bundle(finding(question='Combined certified findings', cited_facts=[first]),
                      finding(finding_id='F2', cited_facts=[second]))
        rendered = render_html(data, report_options(ids=['F1'], sections=[]))
        self.assertIn('Size in bytes: 0', rendered)
        self.assertIn('Recovered entry: False', rendered)
        self.assertIn('User: &lt;u&gt;', rendered)
        self.assertNotIn('Size in bytes: 20', rendered)
        self.assertNotIn('#finding-f2', rendered)
        self.assertNotIn('Combined certified findings</h3>', rendered)
        self.assertIn('<summary>Exact certificate statement</summary>', rendered)
        self.assertEqual(Markup(rendered).sentences, [finding()['english']])

    def test_standalone_literal_sentence_and_full_evidence_have_working_scoped_links(self):
        row = finding(cited_facts=[record(i) for i in (7, 8, 9, 10)])
        data = bundle(row)
        original = copy.deepcopy(data)
        rendered = render_html(data)
        page = Markup(rendered)
        self.assertEqual(page.sentences, [row['english']])
        self.assertEqual(data, original)
        self.assertTrue(rendered.startswith('<!doctype html>'))
        self.assertIn('@media print', rendered)
        self.assertIn('Save as PDF', rendered)
        self.assertIn('Report rendering only.', html.unescape(rendered))
        self.assertIn('proof-f1', page.ids)
        for index in range(1, 5):
            self.assertIn(f'evidence-f1-r{index}', page.ids)
        self.assertTrue(all(link.startswith('#') and link[1:] in page.ids for link in page.links))
        self.assertEqual(len(page.ids), len(set(page.ids)))
        plain = html.unescape(rendered)
        for value in ('synthetic.E01', 'TEST', 'synthetic parser', 'synthetic tool', '4096', 'a' * 64,
                      '1700000000123456 microseconds', '2000000'):
            self.assertIn(value, plain)
        self.assertIn(json.dumps(record()['prov'], sort_keys=True, ensure_ascii=False, indent=2), plain)
        self.assertIn(row['lean'], plain)

    def test_untrusted_text_never_creates_tags_scripts_remote_links_or_attributes(self):
        attack = '</title><script>alert(1)</script><img src="https://evil.test/x" onerror="alert(2)">' \
                 '<a href="javascript:alert(3)">click</a>&'
        proof = '-- Lean is text\n</code></pre><script>alert(4)</script>\n'
        data = bundle(finding(finding_id=attack, english=attack, question=attack, lean=proof,
                              cited_facts=[record(id=attack, obj_text=attack, prov={'artifact': attack})]))
        data['case']['name'] = attack
        data['stats']['verified'] = attack
        rendered = render_html(data)
        page = Markup(rendered)
        self.assertEqual(page.sentences, [attack])
        self.assertFalse(any(tag in {'script', 'img', 'iframe', 'link', 'object', 'embed'} for tag, _ in page.tags))
        self.assertFalse(any(key.startswith('on') or key == 'src' for _, attrs in page.tags for key in attrs))
        self.assertTrue(all(link.startswith('#') for link in page.links))
        self.assertTrue(all(re.fullmatch(r'[a-z]+(?:-[a-z]?\d+)*', anchor) for anchor in page.ids))
        self.assertIn(proof, html.unescape(rendered))
        self.assertIn('Content-Security-Policy', rendered)

    def test_conflicting_copied_rows_are_preserved_and_duplicate_ids_never_collide(self):
        data = bundle(finding(), finding(cited_facts=[record(obj_text='different', row_sha256='b' * 64)]))
        rendered = render_html(data)
        page = Markup(rendered)
        self.assertEqual(rendered.count('Conflicting copied rows share this fact ID.'), 2)
        self.assertIn('evidence-f1-r1', page.ids)
        self.assertIn('evidence-f2-r1', page.ids)
        self.assertIn('proof-f1', page.ids)
        self.assertIn('proof-f2', page.ids)
        self.assertIn('different', rendered)
        self.assertEqual(len(page.ids), len(set(page.ids)))
        self.assertNotIn('Conflicting copied rows', render_html(bundle(finding(), finding())))

    def test_missing_fields_stay_unknown_and_no_file_is_opened_or_proof_executed(self):
        row = finding(cited_facts=[{'id': 7, 'kind': 'fileSeen'}], lean=None, lean_file='../../secret.lean')
        row.pop('axioms')
        data = bundle(row)
        data.pop('stats')
        with patch('builtins.open', side_effect=AssertionError('renderer cannot read files')), \
             patch('subprocess.run', side_effect=AssertionError('renderer cannot execute proofs')):
            rendered = render_html(data)
        plain = html.unescape(rendered)
        for text in ('Unknown — no audit summary', 'Unknown — coverage summary', 'Unknown — claim history',
                     'Unknown — embedded Lean source was not included', 'Unknown — not supplied'):
            self.assertIn(text, plain)
        self.assertNotIn('secret.lean', rendered)
        self.assertNotIn('0 accepted', rendered)

    def test_diagnostics_and_judgments_are_separate_and_do_not_invent_evidence_links(self):
        data = bundle(finding())
        data['rejections'] = [{'finding_id': 'R1', 'reason': 'Serials differ.',
            'proof_gap': {'status': 'diagnostic', 'summary': 'Claim remains unproved.',
                'requirements': [{'category': 'contradictory_identity_or_value', 'reason': 'A differs from B.',
                    'action': 'Seek independent linkage; preserve both serials.', 'fact_ids': [7, 999],
                    'observed': {'left': 'A', 'right': 'B'}, 'required': {'relation': 'same identity'}}],
                'disclaimer': 'Not a certificate; evidence may not exist.'}}]
        data['conclusions'] = [{'conclusion_id': 'J1', 'text': 'This is a synthetic inference.', 'finding_ids': ['F1']}]
        rendered = render_html(data)
        page = Markup(rendered)
        self.assertEqual(page.sentences, [finding()['english'], 'This is a synthetic inference.'])
        self.assertIn('Further evidence or action:', rendered)
        self.assertIn('Seek independent linkage; preserve both serials.', rendered)
        self.assertIn('Proposed fact IDs (not evidence links)', rendered)
        self.assertIn('Unverified judgment', rendered)
        self.assertFalse(any('999' in link for link in page.links))
        self.assertLess(rendered.index('id="needs"'), rendered.index('Claim remains unproved.'))
        self.assertLess(rendered.index('id="judgments"'), rendered.index('This is a synthetic inference.'))

    def test_unverified_or_tampered_status_does_not_become_certified(self):
        data = bundle(finding(status='rejected', english='This claim failed.'))
        rendered = render_html(data)
        self.assertEqual(Markup(rendered).sentences, [])
        self.assertIn('not displayed as certified findings', rendered)
        self.assertIn('This claim failed.', html.unescape(rendered))
        self.assertNotIn('id="proof-f1"', rendered)
        self.assertIn('Report rendering only.', rendered)

    def test_supplied_invalid_audit_and_history_are_diagnostic_coverage_is_not_accuracy(self):
        data = bundle(finding())
        data['audit'] = {'status': 'invalid', 'passed': False, 'count': 4, 'head': 'a' * 64,
                         'problems': ['chain mismatch'], 'path': 'https://evil.test/log'}
        data['coverage'] = {'schema_version': 1, 'extraction': {'status': 'measured', 'record_count': 3},
            'inspection': {'status': 'invalid', 'record_count': 999},
            'citations': {'status': 'unmeasured', 'record_count': 999},
            'questions': {'status': 'measured', 'answered_count': 1, 'unknown_count': 2,
                          'unknown_ids': ['Q2', 'Q3']},
            'failures': {'extraction': {'issues': [{'message': 'Unsupported container'}]}}}
        data['history'] = {'schema_version': 1, 'available': True, 'audit_integrity': {'status': 'failed'},
            'attempts': [{'attempt_id': 'audit:2', 'finding_id': 'F1', 'status': 'duplicate',
                          'duplicate_of': 'F1', 'revises': 'R1', 'revision_status': 'valid'}],
            'unmatched_proposals': [{'attempt_id': 'proposal:3', 'status': 'unknown'}]}
        rendered = render_html(data)
        plain = html.unescape(rendered)
        for text in ('Invalid audit reported', 'Invalid history audit', 'Unknown — unmeasured',
                     'chain mismatch', 'Unsupported container', 'duplicate of F1 (no new proof)',
                     'Proposals with unknown placement', 'answer presence do not establish completeness or accuracy'):
            self.assertIn(text, plain)
        self.assertIn('Q2', plain)
        self.assertNotIn('https://evil.test/log', Markup(rendered).links)
        self.assertNotIn('<td>999</td>', rendered)

    def test_unknown_schema_and_malformed_optional_entries_remain_visible(self):
        data = bundle(finding(cited_facts=[None]))
        data['history'] = {'schema_version': 800, 'message': 'future format'}
        data['coverage'] = {'schema_version': 800, 'message': 'future count'}
        data['rejections'] = [None, {'finding_id': 'R1', 'proof_gap': {'status': 'verified', 'summary': 'not a diagnostic'}}]
        rendered = render_html(data)
        for text in ('Malformed copied record', 'Uninterpreted history summary', 'Uninterpreted coverage summary',
                     'no recognized diagnostic was supplied'):
            self.assertIn(text, rendered)
        self.assertIn('future format', rendered)
        self.assertTrue(all(link[1:] in Markup(rendered).ids for link in Markup(rendered).links))

    def test_examiner_report_holds_only_the_selection_and_says_what_it_left_out(self):
        data = bundle(finding(), finding(finding_id='F2', english='Second sentence.', cited_facts=[record(8)]),
                      finding(finding_id='F3', english='Third sentence.'))
        data['rejections'] = [{'finding_id': 'A9', 'reason': 'not established'}]
        data['conclusions'] = [{'conclusion_id': 'C1', 'text': 'A judgment.', 'finding_ids': ['F2']}]
        data['investigation'] = {'questions': []}
        options = report_options(ids=['F2'], sections=['needs'], reference='REF-7 <i>', examiner='  A. Examiner ')
        rendered = render_html(data, options)
        parsed = Markup(rendered)
        self.assertEqual(parsed.sentences, ['Second sentence.'])
        self.assertIn('finding-f2', parsed.ids)             # keeps the bundle's own numbering
        self.assertNotIn('finding-f1', parsed.ids)
        self.assertIn('<strong>Selected findings only.</strong> This report shows 1 of the 3 entries', rendered)
        self.assertIn('Entries left out are omitted, not refuted.', rendered)
        self.assertIn('Left out of this report: question-by-question plan, investigator judgments, '
                      'full evidence records, Lean proof records, audit, coverage and history.', rendered)
        # cover details are text, labelled as the author's own
        self.assertIn('<dt>Case reference</dt><dd>REF-7 &lt;i&gt;</dd>', rendered)
        self.assertIn('<dt>Examiner</dt><dd>A. Examiner</dd>', rendered)
        self.assertIn('The report author supplies the administrative details and examination notes.', rendered)
        self.assertNotIn('<dt>Organisation</dt>', rendered)
        # sections: refusals kept; judgments, appendices and the plan gone, with no link left dangling
        self.assertIn('id="needs"', rendered)
        for gone in ('id="judgments"', 'id="evidence"', 'id="proofs"', 'id="activity"', 'id="investigation"'):
            self.assertNotIn(gone, rendered)
        self.assertEqual([link for link in parsed.links if link.startswith('#') and link[1:] not in parsed.ids], [])
        # without the appendix, the cited records sit beside the finding
        self.assertIn('<table class="cited">', rendered)
        self.assertIn('<td><strong>8</strong><br><span class="small">fileSeen</span></td>', rendered)
        self.assertIn('Related value: VOL-A', rendered)
        self.assertIn('2023-11-14T22:13:20.123456Z (1700000000123456 microseconds since Unix epoch)'
                      '<br><span class="small">Meaning: record observation</span>', rendered)
        self.assertIn('TEST · synthetic.E01 · test artifact', rendered)
        self.assertIn('Certificate: trust tier kernel', rendered)
        self.assertNotIn('example : True', rendered)

    def test_report_opens_with_summary_evidence_method_and_ends_with_a_sign_off(self):
        zone = 'local time, converted from America/New_York'
        digest = record(9, kind='systemSetting', obj_text='image md5', aux_text='ab' * 16, t=0)
        digest['prov'] = {'exhibit': 'USB <b>1</b>', 'image': 'usb.E01', 'tool': 'reader <i>1.0</i>',
                          'stored_by': 'the imaging tool at acquisition; not recomputed here', 'acquired_with': 'imager 7'}
        timed = record(8, kind='usbInsert', obj_text='SERIAL9')
        timed['prov'] = dict(timed['prov'], time_zone=zone)
        data = bundle(finding(cited_facts=[timed, digest]), finding(finding_id='F2', strength='heuristic'))
        options = report_options(sections=['evidence'], requested_by='Det. <X>', authority='Warrant 7', purpose='p' * 600,
                                 received='2026-11-01', examiner='A. Examiner', report_date='2026-11-14')
        rendered = render_html(data, options)
        parsed = Markup(rendered)
        order = [rendered.index(f'<section id="{name}">') for name in (
            'summary', 'request', 'exhibits', 'method', 'findings', 'disposition', 'signoff', 'glossary', 'evidence')]
        self.assertEqual(order, sorted(order))               # the sign-off closes the report; appendices follow it
        self.assertEqual([link for link in parsed.links if link.startswith('#') and link[1:] not in parsed.ids], [])
        for label, value in (('Requested by', 'Det. &lt;X&gt;'), ('Authority for the request', 'Warrant 7'),
                             ('Evidence received', '2026-11-01'), ('Date of report', '2026-11-14')):
            self.assertIn(f'<dt>{label}</dt><dd>{value}</dd>', rendered)
        # The summary reports record observations without promoting identifier matches to physical events.
        self.assertIn('<div class="key"><h3>Storage records</h3><div><p>The cited records include 1 USB identifier record.', rendered)
        self.assertIn('Matching identifiers do not establish physical-device identity or connection times.', rendered)
        self.assertNotIn('from the supplied examination records', rendered)
        self.assertIn('Each statement is a count or a value from the evidence records that the 2 findings cite.', rendered)
        self.assertIn('1 finding uses a stated heuristic rule.', rendered)
        # evidence items, their stored hash values and the tools are the records' own words, escaped
        self.assertIn('<strong>USB &lt;b&gt;1&lt;/b&gt;</strong>', rendered)
        self.assertIn('<span class="mono">MD5 ' + 'ab' * 16 + '</span> <span class="small">(record 9)</span>', rendered)
        self.assertIn('Imaging tool as recorded: imager 7', rendered)
        self.assertIn('<td>reader &lt;i&gt;1.0&lt;/i&gt;</td><td>Tool</td><td>1</td>', rendered)
        self.assertIn('<td>synthetic parser</td><td>Record reader</td><td>2</td>', rendered)
        self.assertNotIn('<b>1</b>', rendered)
        self.assertNotIn('<i>1.0</i>', rendered)
        self.assertIn('The table lists evidence items that the findings cite.', rendered)
        self.assertIn('<div><span>Examiner</span><strong>A. Examiner</strong></div>', rendered)
        self.assertIn('<div><span>Date of report</span><strong>2026-11-14</strong></div>', rendered)
        self.assertIn('The signature records authorization of this report.', rendered)
        exact = '2023-11-14T22:13:20.123456Z (1700000000123456 microseconds since Unix epoch)'
        if 'The tables use America/New_York local time.' in rendered:   # this system can convert the zone the records name
            self.assertIn('2023-11-14 17:13:20 local (UTC-05:00)<br><span class="small">' + exact + '</span>', rendered)
            self.assertIn('<td>Tue 14 Nov 2023</td><td>1 USB identifier record (17:13)</td>', rendered)
            self.assertIn('<td>SERIAL9</td><td>—</td><td>2023-11-14 17:13; record observation</td>', rendered)
            self.assertIn('Each detailed timestamp includes its offset and Coordinated Universal Time (UTC).' , rendered)
        else:
            self.assertIn('This system could not convert that time zone.', rendered)
        plain = render_html(bundle(finding()))
        self.assertIn('The tables use Coordinated Universal Time (UTC). The cited records contain no local time zone.', plain)
        self.assertIn(exact + '<br><span class="small">Meaning: record observation</span>',
                      render_html(bundle(finding()), report_options(sections=[])))
        self.assertIn('<div><span>Examiner</span><strong></strong></div>', plain)
        for bad in ({'purpose': 'p' * 601}, {'requested_by': 'x' * 201}, {'authority': 'a\tb'}, {'colour': 'red'}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                report_options(**bad)

    def test_links_into_sections_left_out_become_plain_text(self):
        data = bundle(finding(), finding(finding_id='F2'))
        data['case_answers'] = {'questions': [{'question_id': 'Q1', 'certified_findings': [{'finding_id': 'F1'}]}]}
        complete = Markup(render_html(data))
        self.assertIn('#proof-f1', complete.links)
        for sections in (['workflow'], ['workflow', 'evidence'], ['proofs'], []):
            with self.subTest(sections=sections):
                parsed = Markup(render_html(data, report_options(sections=sections)))
                self.assertEqual([link for link in parsed.links if link.startswith('#') and link[1:] not in parsed.ids], [])
                self.assertEqual(len(parsed.sentences), 2)

    def test_report_without_options_is_complete_and_options_are_validated(self):
        data = bundle(finding(), finding(finding_id='F2'))
        complete = render_html(data)
        self.assertEqual(complete, render_html(data, report_options()))
        for section in ('needs', 'judgments', 'evidence', 'proofs', 'activity'):
            self.assertIn(f'id="{section}"', complete)
        self.assertNotIn('Selected findings only', complete)
        self.assertNotIn('Left out of this report', complete)
        everything = render_html(data, report_options(sections=SECTIONS))
        self.assertEqual(complete, everything)
        only_findings = render_html(data, report_options(sections=[]))
        self.assertEqual(len(Markup(only_findings).sentences), 2)
        self.assertNotIn('Selected findings only', only_findings)
        for bad in ({'ids': []}, {'ids': ['F1', 'F1']}, {'ids': ['bad id']}, {'ids': ['x'] * 2001}, {'ids': [7]},
                    {'sections': ['findings']}, {'sections': ['needs', 'needs']}, {'examiner': 'x' * 201},
                    {'reference': 'line\nbreak'}, {'organisation': 5}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                report_options(**bad)
        with self.assertRaises(ValueError):                 # not a verified finding in this bundle
            render_html(data, report_options(ids=['F9']))
        with self.assertRaises(ValueError):                 # an ID the bundle repeats cannot be chosen
            render_html(bundle(finding(), finding()), report_options(ids=['F1']))
        with self.assertRaises(ValueError):                 # a duplicate must not cancel an absent selected ID
            render_html(bundle(finding(), finding(english='Conflicting copy.')),
                        report_options(ids=['F1', 'MISSING']))
        unverified = bundle(finding(status='proposed'))
        with self.assertRaises(ValueError):
            render_html(unverified, report_options(ids=['F1']))

    def test_empty_bundle_has_explicit_unknowns_and_rejects_non_object_input(self):
        rendered = render_html({})
        self.assertIn('Untitled investigation', rendered)
        self.assertIn('No entries marked verified were supplied', rendered)
        self.assertIn('No refusal details were supplied', rendered)
        self.assertIn('Unknown', rendered)
        with self.assertRaises(TypeError):
            render_html([])


if __name__ == '__main__':
    unittest.main()
