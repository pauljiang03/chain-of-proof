"""Cross-record review must not turn common forensic patterns into contradictions."""
from copy import deepcopy
import json
import unittest

from agent.review import review
from checker.facts import Fact


class Source:
    def __init__(self, rows=(), strings=None):
        self.rows = list(rows)
        self.strings = {0: '', 1: 'Report.docx', 2: 'VALUE-A', 3: 'VALUE-B', 4: 'SHARED LABEL',
                        5: 'Other entity', **(strings or {})}

    def all(self):
        return self.rows

    def string(self, sid):
        return self.strings.get(sid, f'#{sid}')


def fact(fid=1, *, kind='systemSetting', t=100, res=2, obj=1, aux=2, prov=None, **updates):
    provenance = {'image': 'test.E01', 'exhibit': 'PC', 'artifact': 'source.bin',
                  'observation_id': 'row-12', 'time_meaning': 'stored field timestamp'} if prov is None else dict(prov)
    provenance.update(updates)
    return Fact(fid, kind, t, res, obj, aux, provenance)


def categories(result):
    return [row['category'] for row in result['diagnostics']]


class RecordReview(unittest.TestCase):
    def test_label_reuse_is_ambiguity_not_a_false_fact_or_device_identification(self):
        source = Source([fact(kind='volumeSeen', obj=4), fact(2, kind='volumeSeen', obj=4, aux=3)])
        result = review(source)
        self.assertEqual(categories(result), ['identity_label_ambiguity'])
        diagnostic = result['diagnostics'][0]
        self.assertEqual(diagnostic['record_ids'], [1, 2])
        self.assertIn('legitimately', diagnostic['why'])
        self.assertIn('not a factual contradiction', ' '.join(result['limitations']))
        self.assertEqual(diagnostic['status'], 'diagnostic')
        self.assertEqual(diagnostic['records'][1]['aux_text'], 'VALUE-B')
        self.assertEqual(diagnostic['records'][0]['row_sha256'], source.rows[0].row_sha256())

    def test_scope_keeps_images_exhibits_snapshots_and_independent_sources_apart(self):
        for update in ({'image': 'other.E01'}, {'exhibit': 'OTHER'}, {'snapshot_id': 'older'},
                       {'source_path': 'other.bin'}, {'artifact': 'other-source.bin'},
                       {'source_file': 'other.sqlite'}, {'browser': 'other browser'},
                       {'observation_id': 'other-row'}, {'time_meaning': 'a different field'}):
            with self.subTest(update=update):
                self.assertEqual(review(Source([fact(), fact(2, aux=3, t=800, **update)]))['diagnostics'], [])
        self.assertEqual(review(Source([fact(kind='volumeSeen', obj=4),
                                       fact(2, kind='volumeSeen', obj=4, aux=3, image='other.E01')]))['diagnostics'], [])

    def test_exact_observation_conflicting_value_is_reported_without_choosing_truth(self):
        result = review(Source([fact(), fact(2, aux=3)]))
        self.assertEqual(categories(result), ['same_observation_value_disagreement'])
        self.assertEqual(result['diagnostics'][0]['observed']['values'], ['VALUE-A', 'VALUE-B'])
        self.assertIn('does not select the true value', result['diagnostics'][0]['why'])
        # Same textual value under two interned IDs is not a semantic value disagreement.
        self.assertEqual(review(Source([fact(), fact(2, aux=3)], {3: 'VALUE-A'}))['diagnostics'], [])

    def test_same_event_disjoint_times_require_exact_meaning_and_preserve_uncertainty(self):
        self.assertEqual(categories(review(Source([fact(), fact(2, t=200)]))), ['same_observation_time_disagreement'])
        for second in (fact(2, t=103), fact(2, t=104), fact(2, t=300, res=200),
                       fact(2, t=200, time_meaning='last access, not creation')):
            with self.subTest(second=second):
                self.assertEqual(review(Source([fact(), second]))['diagnostics'], [])

    def test_repeated_legitimate_events_and_generic_event_type_ids_do_not_establish_identity(self):
        rows = [fact(kind='webVisit', prov={'image': 'pc', 'artifact': 'History', 'record_id': 'https://example.test',
                                          'event_id': 12, 'time_meaning': 'visit time'}),
                fact(2, kind='webVisit', t=900, prov={'image': 'pc', 'artifact': 'History', 'record_id': 'https://example.test',
                                                   'event_id': 12, 'time_meaning': 'visit time'})]
        self.assertEqual(review(Source(rows))['diagnostics'], [])
        self.assertEqual(review(Source([fact(kind='webVisit'), fact(2, kind='webVisit', t=900, observation_id='later-visit')]))['diagnostics'], [])
        self.assertEqual(review(Source([fact(kind='fileCreated', t=900), fact(2, kind='fileModified', t=10)]))['diagnostics'], [])
        self.assertEqual(review(Source([fact(kind='emailSent'), fact(2, kind='emailSent', aux=3)]))['diagnostics'], [])

    def test_examination_times_are_not_pretended_to_be_one_historical_event(self):
        for semantics in ({'timestamp_semantics': 'examination_observation'},
                          {'time_meaning': 'when the image was examined, not an event on the device'}):
            self.assertEqual(review(Source([fact(kind='fileContent', **semantics),
                                           fact(2, kind='fileContent', t=500, **semantics)]))['diagnostics'], [])

    def test_explicit_single_event_order_conflict_without_inferred_lifecycle_order(self):
        base = {'event_instance_id': 'operation-17', 'event_meaning': 'one recorded transfer'}
        start = fact(timestamp_role='start', t=200, **base)
        end = fact(2, timestamp_role='end', t=100, time_meaning='stored end field', **base)
        result = review(Source([start, end]))
        self.assertEqual(categories(result), ['explicit_event_order_conflict'])
        self.assertEqual(result['diagnostics'][0]['observed']['start_interval_us'], [198, 202])
        for changed in (fact(2, timestamp_role='end', t=199, **base),
                        fact(2, timestamp_role='end', t=100, event_instance_id='different-event', event_meaning='one recorded transfer'),
                        fact(2, timestamp_role='end', t=100, obj=5, **base),
                        fact(2, timestamp_role='end', t=100, artifact='other.bin', **base),
                        fact(2, timestamp_role='end', t=100, event_meaning='one recorded transfer')):
            # Different roles need different timestamp meanings for the observation-time rule.
            changed = Fact(changed.id, changed.kind, changed.t, changed.res, changed.obj, changed.aux,
                           {**changed.prov, 'time_meaning': 'stored end field'})
            self.assertEqual(review(Source([start, changed]))['diagnostics'], [])

    def test_missing_scope_or_locator_does_not_create_a_conflict(self):
        for prov in ({}, {'image': 'pc', 'time_meaning': 'creation'},
                     {'image': 'pc', 'artifact': 'a file', 'time_meaning': 'creation'},
                     {'image': 'pc', 'artifact': 'table', 'row_id': 2, 'time_meaning': 'creation'}):
            self.assertEqual(review(Source([fact(prov=prov), fact(2, aux=3, t=900, prov=prov)]))['diagnostics'], [])
        prov = {'image': 'pc', 'artifact': 'History', 'table': 'visits', 'row_id': 2, 'time_meaning': 'visit'}
        self.assertEqual(categories(review(Source([fact(prov=prov), fact(2, aux=3, prov=prov)]))), ['same_observation_value_disagreement'])

    def test_scan_and_output_limits_are_explicit_and_no_source_mutation(self):
        rows = [fact(), fact(2, aux=3), fact(3, t=300), fact(4, t=400)]
        source = Source(rows)
        before = deepcopy(rows)
        result = review(source, max_records=3, max_diagnostics=1)
        self.assertTrue(result['scope']['scan_truncated'])
        self.assertTrue(result['scope']['diagnostics_truncated'])
        self.assertEqual(result['scope']['records_examined'], 3)
        self.assertEqual(len(result['diagnostics']), 1)
        self.assertEqual(source.rows, before)
        result['diagnostics'][0]['records'][0]['prov']['image'] = 'mutated output'
        self.assertEqual(source.rows[0].prov['image'], 'test.E01')
        self.assertEqual(review(source), review(source))
        self.assertEqual(json.loads(json.dumps(review(source)))['status'], 'diagnostic')

    def test_capped_iterable_stops_consumption_and_unknown_rows_do_not_crash(self):
        consumed = []
        def rows():
            for index in range(100):
                consumed.append(index)
                yield fact(index + 1)
        source = Source()
        source.all = lambda: self.fail('explicit subset must not load source.all()')
        result = review(source, rows(), max_records=2)
        self.assertEqual(len(consumed), 3)  # One look-ahead establishes truncation.
        self.assertTrue(result['scope']['scan_truncated'])
        self.assertEqual(result['scope']['input'], 'supplied_subset')
        self.assertEqual(review(source, [None, {}, {'id': True}])['scope']['records_unusable'], 3)
        for kwargs in ({'max_records': True}, {'max_records': 0}, {'max_diagnostics': 0}):
            with self.assertRaises(ValueError):
                review(source, [], **kwargs)


if __name__ == '__main__':
    unittest.main()
