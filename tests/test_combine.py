"""The saved-run union adds complementary proof-backed coverage without a judge."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from checker.check import check
from checker.combine import combine
from checker.export import bundle
from checker.facts import open_source
from eval.score import score_run
from verifier.verify import verify


ROOT = Path(__file__).resolve().parent.parent
FACTS = ROOT / 'fixtures' / 'sample_facts.json'


class CombineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root = Path(cls.tmp.name)
        cls.source = open_source(FACTS)
        first, second = cls.root / 'first', cls.root / 'second'
        # Duplicate claim in the first run; colliding certificate ID in the second.
        for claim, fid, out in [({'searched': [3100]}, 'A001', first),
                                ({'searched': [3100]}, 'A002', first),
                                ({'usbConnected': [4512]}, 'A001', second)]:
            cert = check(claim, fid, cls.source, out_dir=out)
            if cert['status'] != 'verified':
                raise AssertionError(cert)
        cls.first = bundle(first, 'Synthetic evidence')
        cls.second = bundle(second, 'Synthetic evidence')
        cls.first['conclusions'] = [{'conclusion_id': 'C1', 'text': 'UNCHECKED INVENTED MOTIVE',
                                     'finding_ids': ['A001'], 'strength': 'judgment'}]
        rejected = {'finding_id': 'R1', 'claim': {'searched': [4512]}, 'status': 'rejected'}
        cls.first['rejections'] = [rejected]
        cls.first['findings'].append(rejected)
        cls.first['stats']['rejected'] = 1
        cls.paths = [cls.root / 'first.json', cls.root / 'second.json']
        cls.paths[0].write_text(json.dumps(cls.first))
        cls.paths[1].write_text(json.dumps(cls.second))
        cls.out = cls.root / 'combined'
        cls.combined = combine(cls.paths, FACTS, cls.out, workers=2)

    def write_run(self, name, findings):
        path = self.root / f'{name}.json'
        path.write_text(json.dumps({'findings': findings}))
        return path

    def write_facts(self, name, mutate):
        data = json.loads(FACTS.read_text())
        mutate(data)
        path = self.root / f'{name}.json'
        path.write_text(json.dumps(data))
        return path

    def test_union_certificates_are_reissued_and_kernel_verify(self):
        findings = self.combined['findings']
        self.assertEqual([f['finding_id'] for f in findings], ['F000001', 'F000002'])
        self.assertEqual([f['claim'] for f in findings],
                         [{'searched': [3100]}, {'usbConnected': [4512]}])
        for finding in findings:
            self.assertEqual(verify(finding, self.source), [])
            self.assertIn(f"namespace Cert.{finding['finding_id']}", finding['lean'])
            self.assertNotIn('namespace Cert.A001', finding['lean'])
        self.assertEqual(self.combined['stats']['verified'], 2)
        self.assertEqual(self.combined['stats']['rejected'], 0)
        self.assertFalse(self.combined['case']['new_ai_run'])
        self.assertFalse(self.combined['case']['new_facts'])

    def test_complementary_rows_increase_deterministic_score(self):
        # This synthetic reference is used only by the test, never by combine().
        reference = {'tolerance_s': 0, 'items': [
            {'id': 'search', 'question': 'Search',
             'expect': {'kind': 'webSearch', 'obj': 'sample data leakage methods'}},
            {'id': 'usb', 'question': 'Device',
             'expect': {'kind': 'usbInsert', 'obj': 'SAMPLE-SERIAL-RM2'}}]}
        first = dict(self.first, findings=[f for f in self.first['findings']
                                          if f['status'] == 'verified'])
        counts = [sum(i['certified'] for i in score_run(reference, run)['items'])
                  for run in (first, self.second, self.combined)]
        self.assertEqual(counts, [1, 1, 2])

    def test_deduplication_retains_source_provenance_and_excludes_prose(self):
        self.assertEqual(self.combined['composition']['input_certified_findings'], 3)
        self.assertEqual(self.combined['composition']['duplicate_claims_removed'], 1)
        self.assertEqual(self.combined['composition']['source_rejected_proposals'], 1)
        self.assertEqual(self.combined['composition']['excluded_unverified_conclusions'], 1)
        self.assertEqual(self.combined['sources'][0]['nonverified_findings_ignored'], 1)
        self.assertEqual(self.combined['conclusions'], [])
        self.assertEqual(self.combined['rejections'], [])
        report = (self.out / 'report.md').read_text()
        self.assertNotIn('UNCHECKED INVENTED MOTIVE', report)
        self.assertIn('not a new AI investigation', report)
        self.assertIn('no answer key or reference was used', report)
        mapping = json.loads((self.out / 'source_map.json').read_text())
        self.assertEqual([f['finding_id'] for f in mapping['findings']['F000001']], ['A001', 'A002'])
        self.assertEqual(mapping['findings']['F000002'][0]['finding_id'], 'A001')
        self.assertTrue(all(len(s['sha256']) == 64 for s in mapping['sources']))

    def test_input_order_and_repeated_paths_do_not_change_ids_or_claims(self):
        other = combine([self.paths[1], self.paths[0], self.paths[1]], FACTS,
                        self.root / 'reordered', workers=2)
        selected = lambda run: [(f['finding_id'], f['claim'], f['source_findings'])
                                for f in run['findings']]
        self.assertEqual(selected(other), selected(self.combined))
        self.assertEqual(other['composition'], self.combined['composition'])

    def test_existing_output_is_never_overwritten(self):
        before = (self.out / 'run.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'refusing to overwrite'):
            combine(self.paths, FACTS, self.out)
        self.assertEqual((self.out / 'run.json').read_bytes(), before)

    def test_changed_rows_and_changed_interned_strings_are_rejected(self):
        def change_row(data):
            next(f for f in data['facts'] if f['id'] == 3100)['t'] += 1
        for name, mutate in [('changed-row', change_row),
                             ('changed-string', lambda d: d['strings'].update({'700': 'other search'}))]:
            with self.subTest(name=name):
                out = self.root / f'{name}-out'
                changed = self.write_facts(name, mutate)
                with self.assertRaisesRegex(ValueError, 'does not match --facts'):
                    combine(self.paths, changed, out)
                self.assertFalse(out.exists())

    def test_duplicate_source_ids_cannot_denote_different_claims(self):
        path = self.write_run('duplicate-id', [self.first['findings'][0], self.second['findings'][0]])
        out = self.root / 'duplicate-id-out'
        with self.assertRaisesRegex(ValueError, 'denotes different claims'):
            combine([path], FACTS, out)
        self.assertFalse(out.exists())

    def test_census_requires_exact_current_membership(self):
        # The original row still hashes identically, but another row joins the census.
        old = copy.deepcopy(self.first['findings'][0])
        old['claim'] = {'exactly': ['webSearch', 1]}
        path = self.write_run('census', [old])
        def grow(data):
            row = dict(next(f for f in data['facts'] if f['id'] == 3100), id=99999)
            data['facts'].append(row)
        changed = self.write_facts('grown', grow)
        out = self.root / 'grown-out'
        with self.assertRaisesRegex(ValueError, 'different evidence membership'):
            combine([path], changed, out)
        self.assertFalse(out.exists())

    def test_source_status_does_not_bypass_real_kernel(self):
        forged = copy.deepcopy(self.first['findings'][0])
        forged['claim'] = {'usbConnected': [3100]}  # hashes match, but its kind is a search
        path = self.write_run('forged', [forged])
        out = self.root / 'forged-out'
        with self.assertRaisesRegex(ValueError, 'merged claim no longer certifies'):
            combine([path], FACTS, out)
        self.assertFalse((out / 'run.json').exists())
        self.assertFalse((out / 'report.md').exists())


if __name__ == '__main__':
    unittest.main()
