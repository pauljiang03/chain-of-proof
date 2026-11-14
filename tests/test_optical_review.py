"""Regressions for drive-lock interpretation and the original C008 inference."""
import json
from pathlib import Path
import tempfile
import unittest

from agent.consistency import optical_conflicts, seconds
from agent.conclusions import Conclusions
from checker import claims
from checker.facts import open_source

ROOT = Path(__file__).resolve().parent.parent


class OpticalReview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved_run = json.loads((ROOT / 'fixtures/optical_regression.json').read_text())
        cls.src = open_source(ROOT / 'evidence/case_facts.json')

    def sentence(self, name):
        f = next(f for f in self.saved_run['findings'] if f['finding_id'] == name)
        c = claims.parse(f['claim'])
        _, facts = claims.cited_facts(c, self.src)
        return claims.english(c, facts, self.src)

    def test_burn_template_does_not_promote_a_lock_or_settings_change_to_a_write(self):
        text = self.sentence('A073')
        self.assertIn('event 133', text)
        self.assertIn('exclusive-access lock', text)
        self.assertIn('configuration change', text)
        self.assertNotIn('Windows leaves this trace when it writes', text)
        self.assertIn('does not establish a write', text)

    def test_recovery_and_label_templates_do_not_invent_filesystem_or_device_identity(self):
        self.assertNotIn("before the device's current file system", self.sentence('A077'))
        self.assertIn('older states of the same file system', self.sentence('A077'))
        self.assertNotIn('earlier file system', self.sentence('A080'))
        self.assertIn('different devices can share it', self.sentence('A079'))

    def test_original_inference_is_refused_even_though_all_its_time_tokens_are_cited(self):
        c = next(c for c in self.saved_run['conclusions'] if c['conclusion_id'] == 'C008')
        with tempfile.TemporaryDirectory() as tmp:
            result = Conclusions(tmp).add(c['text'], c['finding_ids'], self.saved_run['findings'], 'test')
            self.assertEqual(result['status'], 'rejected')
            self.assertTrue(any('no physical-disc link' in s for s in result['conflicts']))
            self.assertTrue(any('ends before its UDF' in s for s in result['conflicts']))
            self.assertEqual(Conclusions(tmp).all(), [])

    def test_guard_works_for_another_exhibit_and_accepts_a_statement_of_uncertainty(self):
        when = '2020-01-02 12:00:00 UTC'
        rows = [{'id': 1, 'kind': 'cdBurn', 't': seconds(when) * 1_000_000,
                 'prov': {'exhibit': 'PC'}}]
        findings = [{'cited_facts': rows}]
        self.assertTrue(optical_conflicts(f'disc X9 was burned at {when}.', findings))
        self.assertEqual(optical_conflicts(f'disc X9 was not burned at {when}.', findings), [])
        self.assertEqual(optical_conflicts('The lock does not identify disc X9.', findings), [])
        rows.append({'id': 2, 'kind': 'fileCreated', 't': seconds(when) * 1_000_000,
                     'prov': {'exhibit': 'X9'}})
        self.assertEqual(optical_conflicts(f'disc X9 was written at {when}.', findings), [])
        # Passing a narrow check is not a proof of this assertion.

    def test_reversed_window_is_rejected(self):
        self.assertTrue(optical_conflicts('disc T7 was written between '
                         '2020-01-02 12:00:00 UTC and 2020-01-01 12:00:00 UTC.', []))


if __name__ == '__main__':
    unittest.main()
