"""Workflow reports keep supplied work notes outside the certificate boundary."""
from copy import deepcopy
import html
import unittest

from agent.answers import build_answers
from agent.review import review
from app.report import render_html
from checker.report import render
from tests.test_app_report import Markup, bundle, finding
from tests.test_report_citations import outside_fences
from tests.test_review import Source, fact


def workflow():
    data = bundle(finding(question='Q-one'))
    data['case']['case_id'] = 'synthetic-case'
    plan = {'schema_version': 1, 'case_id': 'synthetic-case', 'name': 'Public case', 'revision': 3,
            'questions': [{'id': 'Q-one', 'prompt': 'What is recorded?', 'work_status': 'reviewed',
                           'finding_ids': ['F1'], 'searched': ['Reported search of shortcuts'],
                           'unresolved': ['Device identity still unresolved'], 'next_actions': ['Inspect device serials']},
                          {'id': 'Q-two', 'prompt': 'Which device?', 'work_status': 'blocked',
                           'finding_ids': [], 'searched': [], 'unresolved': ['No device link'], 'next_actions': []}]}
    data['investigation'] = plan
    data['case_answers'] = build_answers(data, plan)
    data['conflicts'] = review(Source([fact(kind='volumeSeen', obj=4), fact(2, kind='volumeSeen', obj=4, aux=3)]))
    return data


class WorkflowReports(unittest.TestCase):
    def test_actual_answer_builder_and_review_render_all_questions_with_bound_sentences(self):
        data = workflow()
        before = deepcopy(data)
        html_report = render_html(data)
        markdown = render(data)
        page = Markup(html_report)
        self.assertTrue(all(target.startswith('#') and target[1:] in page.ids for target in page.links))
        self.assertEqual(len(page.ids), len(set(page.ids)))
        self.assertEqual(page.sentences, [finding()['english'], finding()['english']])
        for rendered in (html.unescape(html_report), html.unescape(markdown)):
            for text in ('Question-by-question findings', 'Q-one', 'Q-two', 'No bound certificate statement',
                         'Agent-reported work status', 'Device identity still unresolved', 'Inspect device serials',
                         'not certified contradictions', 'One label is associated with different recorded volume identities',
                         'Reported association', 'not a proof that the question is answered'):
                self.assertIn(text, rendered)
        self.assertEqual(data, before)

    def test_forged_or_unbound_answer_sentences_are_preserved_only_as_unverified_content(self):
        for mutate in (lambda d: d['case_answers']['questions'][0]['certified_findings'][0].update(sentence='UNTRUSTED invented answer'),
                       lambda d: d['findings'][0].update(status='rejected'),
                       lambda d: d['findings'].append(deepcopy(d['findings'][0])),
                       lambda d: d['case_answers']['questions'][0]['certified_findings'][0].update(finding_id='missing')):
            data = workflow()
            mutate(data)
            html_report, markdown = render_html(data), render(data)
            question_part = html_report.split('<section id="answers">', 1)[1].split('<section id="conflicts">', 1)[0]
            md_part = markdown.split('## Question-by-question findings', 1)[1].split('## Cross-record review', 1)[0]
            self.assertNotIn('class="sentence"', question_part)
            self.assertNotIn('**Recorded certificate statement', md_part)
            self.assertIn('no matching unique current-run certificate sentence', question_part)
            self.assertIn('No bound certificate statement', md_part)
        data = workflow()
        data['findings'].extend([None, {'status': 'unknown', 'english': 'UNTRUSTED legacy text'}])
        self.assertIn('UNTRUSTED legacy text', render(data))
        self.assertIn('not displayed as certified findings', render(data))

    def test_truncation_and_empty_or_unknown_review_are_never_a_clean_bill_of_health(self):
        data = workflow()
        data['conflicts']['scope']['scan_truncated'] = True
        for rendered in (render_html(data), render(data)):
            self.assertIn('REVIEW TRUNCATED', rendered)
        data['conflicts'] = review(Source([]))
        for rendered in (render_html(data), render(data)):
            self.assertIn('not a finding that the evidence is consistent', rendered)
        data['conflicts'] = {'schema_version': 7, 'status': 'verified', 'note': 'UNKNOWN REVIEW'}
        for rendered in (render_html(data), render(data)):
            self.assertIn('supported diagnostic review is unavailable', rendered)
            self.assertIn('UNKNOWN REVIEW', rendered)

    def test_unavailable_workflow_and_wrong_case_stay_uninterpreted(self):
        data = workflow()
        data['investigation'] = {'schema_version': 1, 'status': 'unavailable', 'reason': 'No public questions'}
        data['case_answers']['case_id'] = 'other-case'
        for rendered in (render_html(data), render(data)):
            self.assertIn('supported investigation plan is unavailable', rendered)
            self.assertIn('not bound to this case', rendered)
        self.assertEqual(Markup(render_html(data)).sentences, [finding()['english']])

    def test_failed_final_review_is_unavailable_not_zero_diagnostics(self):
        data = workflow()
        data['conflicts'] = {'schema_version': 1, 'status': 'unavailable', 'diagnostics': [],
                             'reason': 'Final conflict review failed; no consistency conclusion is available.',
                             'error_type': 'RuntimeError'}
        for rendered in (render_html(data), render(data)):
            self.assertIn('Conflict review unavailable', rendered)
            self.assertIn('Final conflict review failed', rendered)
            self.assertIn('RuntimeError', rendered)
            self.assertNotIn('No matching diagnostics were recorded', rendered)

    def test_untrusted_notes_diagnostics_and_paths_cannot_inject_markup_or_links(self):
        attack = '<script>alert(1)</script><img src=x onerror=alert(2)> [fake](javascript:evil)'
        data = workflow()
        data['investigation']['questions'][0].update(prompt=attack, searched=[attack], previous_run_notes={'status': 'unverified', 'next_actions': [attack]})
        data['case_answers']['questions'][0].update(prompt=attack, next_actions=[attack])
        diagnostic = data['conflicts']['diagnostics'][0]
        diagnostic.update(id=attack, summary=attack, why=attack, required=attack)
        diagnostic['records'][0]['prov']['artifact'] = attack
        data['collection'] = {'status': 'completed_with_limitations', 'continuation_required': True,
                              'facts': attack, 'config': attack, 'health': attack, 'note': attack}
        html_report, markdown = render_html(data), render(data)
        page = Markup(html_report)
        self.assertFalse(any(tag in ('script', 'img', 'iframe') for tag, _ in page.tags))
        self.assertTrue(all(link.startswith('#') and link[1:] in page.ids for link in page.links))
        visible = outside_fences(markdown)
        self.assertNotIn('<script', visible)
        self.assertNotIn('javascript:', visible)
        self.assertIn(attack, html.unescape(html_report))
        self.assertIn(attack, html.unescape(visible))

    def test_new_collection_is_separate_and_previous_notes_do_not_become_proofs(self):
        data = workflow()
        data['collection'] = {'status': 'completed', 'continuation_required': True,
                              'facts': '/tmp/new-facts.json', 'config': '/tmp/new-config.json',
                              'health': '/tmp/new-health.json', 'facts_sha256': 'a' * 64, 'snapshot_id': 'next'}
        previous = {'status': 'unverified', 'searched': ['Prior search'], 'unresolved': ['Prior gap'], 'next_actions': ['Prior action']}
        data['investigation']['questions'][1]['previous_run_notes'] = previous
        data['case_answers']['questions'][1]['previous_run_notes'] = previous
        for rendered in (html.unescape(render_html(data)), html.unescape(render(data))):
            self.assertIn('New evidence available', rendered)
            self.assertIn('not incorporated into the current findings', rendered)
            self.assertIn('query the new records and issue new proofs', rendered)
            self.assertIn('/tmp/new-facts.json', rendered)
            self.assertIn('Previous-run notes — unverified', rendered)
        data['collection']['continuation_required'] = False
        for rendered in (render_html(data), render(data)):
            self.assertIn('not established by this receipt', rendered)


if __name__ == '__main__':
    unittest.main()
