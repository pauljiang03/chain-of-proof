"""The case brief only counts what a bundle's own cited records say. Synthetic bundles only."""
import re
import unittest
from datetime import datetime, timezone
from pathlib import Path

from app import brief

STATIC = Path(__file__).resolve().parents[1] / 'app' / 'static'
NEW_YORK = 'local time, converted from America/New_York'


def micro(*parts):
    return int(datetime(*parts, tzinfo=timezone.utc).timestamp()) * 1000000


def row(number, kind, obj, aux=None, t=0, **prov):
    return {'id': number, 'kind': kind, 't': t, 'obj_text': obj, 'aux_text': aux, 'prov': prov}


def finding(name, rows, **updates):
    return {'finding_id': name, 'status': 'verified', 'strength': 'strong', 'trust_tier': 'kernel', 'axioms': [],
            'proposer': 'miner', 'cited_facts': rows, **updates}


USB = row(1, 'usbInsert', 'SERIAL9', t=micro(2015, 3, 24, 2, 30), exhibit='PC', image='pc.E01', tool='reader 1.0',
          time_zone=NEW_YORK, time_meaning='first connection')
DELETED = row(2, 'fileDeleted', r'C:\a.txt', t=micro(2015, 3, 24, 5, 0), exhibit='PC', image='pc.E01', tool='reader 1.0',
              time_meaning='deletion time')
HOST = row(3, 'systemSetting', 'computer name', 'HOST-1', exhibit='PC', image='pc.E01', tool='reader 1.0')
SYSTEM = row(4, 'systemSetting', 'operating system', 'Windows 7', exhibit='PC', image='pc.E01', tool='reader 1.0')
DIGEST = row(5, 'systemSetting', 'image md5', 'ab' * 16, t=micro(2026, 11, 14, 0, 0), exhibit='USB#2', image='usb2.E01',
             tool='reader 1.0', stored_by='the imaging tool at acquisition; not recomputed here',
             acquired_as_recorded='1427484093', acquired_with='version 7',
             time_meaning='when the image was examined, not an event on the device', artifact="usb2.E01: 'digest' section")
VOLUME = row(6, 'volumeOnDevice', 'SERIAL9', 'AAAA-BBBB', exhibit='USB#2', image='usb2.E01', tool='reader 1.0')
OTHER = row(7, 'fileSeen', 'x', exhibit='USB#10', image='usb10.E01', parser='own reader')
LABEL = row(8, 'tag', 'SERIAL9', 'unauthorized-device')


def bundle():
    return {'case': {'name': 'Synthetic', 'note': 'A synthetic fixture.'},
            'findings': [finding('F1', [USB, HOST, SYSTEM, DIGEST, VOLUME, OTHER, LABEL]),
                         finding('F2', [USB, DELETED], strength='heuristic'),
                         finding('F3', [row(9, 'emailSent', 'never counted', exhibit='LAPTOP')], status='proposed'),
                         'not a finding'],
            'rejections': [{'finding_id': 'A1'}], 'conclusions': []}


class Brief(unittest.TestCase):
    def test_record_type_table_matches_the_timeline(self):
        source = (STATIC / 'timeline.js').read_text(encoding='utf-8')
        block = re.search(r'const KINDS = \{\n(.*?)\n  \};', source, re.S).group(1)
        table = {name: (lane, one, many, marked == 'true') for name, lane, one, many, marked in
                 re.findall(r'^\s+(\w+): \["(\w+)", "([^"]*)", "([^"]*)", (true|false)\],$', block, re.M)}
        self.assertEqual(len(table), len(block.strip().splitlines()))      # every line was understood
        self.assertEqual(table, brief.KINDS)
        self.assertEqual(tuple(re.findall(r'\{ key: "(\w+)", name: "([^"]*)" \}', source)), brief.LANES)

    def test_counts_exhibits_tools_and_limits_come_from_cited_records_of_verified_findings(self):
        info = brief.build(bundle())
        self.assertEqual(info['counts'], {'findings': 2, 'recorded': 2, 'firm': 1, 'likely': 1, 'refused': 1,
                                          'judgments': 0, 'records': 8, 'dated': 2, 'undated': 6})
        self.assertEqual([item['label'] for item in info['exhibits']], ['PC', 'USB#2', 'USB#10'])   # natural order
        pc, usb, last = info['exhibits']
        self.assertEqual((pc['images'], pc['records'], pc['findings']), (['pc.E01'], 4, 2))
        self.assertEqual(pc['system'], [{'label': 'Computer name', 'values': ['HOST-1']},
                                        {'label': 'Operating system', 'values': ['Windows 7']}])
        self.assertEqual((usb['devices'], usb['volumes'], usb['acquired'], usb['tools']),
                         (['SERIAL9'], ['AAAA-BBBB'], ['1427484093'], ['version 7']))
        self.assertEqual(usb['digests'], [{'algorithm': 'MD5', 'value': 'ab' * 16, 'record': 5,
                                           'source': "usb2.E01: 'digest' section",
                                           'stored_by': 'the imaging tool at acquisition; not recomputed here'}])
        self.assertEqual((last['digests'], last['records']), ([], 1))
        self.assertEqual(info['unlabelled'], 1)                              # the label record names no exhibit
        self.assertEqual(info['tools'], [{'name': 'reader 1.0', 'count': 6}])
        self.assertEqual(info['readers'], [{'name': 'own reader', 'count': 1}])
        self.assertEqual(info['checker']['axioms'], [{'name': 'none', 'count': 2}])
        self.assertNotIn('LAPTOP', str(info))                                # a proposal that is not verified adds nothing
        limits = {item['key']: item['text'] for item in info['limits']}
        self.assertIn('1 of 2 findings rest on a stated rule of thumb', limits['likely'])
        self.assertIn('They were not recomputed here.', limits['hashes'])
        self.assertIn('6 of 8 cited records carry no event time', limits['undated'])
        self.assertTrue(limits['refused'].startswith('1 proposed finding was refused'))
        self.assertEqual(limits['note'], 'Note stored with this run: A synthetic fixture.')
        self.assertIn('does not check that the tools read the disk images correctly', limits['readers'])

    def test_days_follow_the_zone_the_records_name_and_examination_time_is_not_an_event(self):
        info = brief.build(bundle())
        self.assertEqual((info['zone']['name'], info['zone']['records']), ('America/New_York', 1))
        self.assertEqual(info['range'], {'from': USB['t'], 'to': DELETED['t']})   # the 2026 digest time is left out
        self.assertEqual(info['busiest'], {'from': USB['t'], 'to': DELETED['t'], 'records': 2})
        days = [(day['date'], [(group['kind'], group['count']) for group in day['events']]) for day in info['days']]
        if info['zone']['known']:   # 02:30 UTC is still the evening of the 23rd in New York
            self.assertEqual(days, [('2015-03-23', [('usbInsert', 1)]), ('2015-03-24', [('fileDeleted', 1)])])
            self.assertNotIn('zone', {item['key'] for item in info['limits']})
        else:
            self.assertEqual(days, [('2015-03-24', [('usbInsert', 1), ('fileDeleted', 1)])])
        plain = brief.build({'findings': [finding('F1', [DELETED])]})
        self.assertIsNone(plain['zone'])
        self.assertEqual(plain['days'][0]['date'], '2015-03-24')
        limits = {item['key']: item['text'] for item in plain['limits']}
        self.assertIn('so times are in UTC', limits['zone'])
        self.assertIn('No image hash value is among the cited records', limits['hashes'])
        unknown = brief.build({'findings': [finding('F1', [dict(DELETED, prov={'time_zone': 'from America/Not_A_Zone'})])]})
        self.assertEqual((unknown['zone']['name'], unknown['zone']['known']), ('America/Not_A_Zone', False))
        self.assertIn('cannot convert', {item['key']: item['text'] for item in unknown['limits']}['zone'])

    def test_summary_keeps_examination_and_unknown_times_off_the_source_timeline(self):
        stamp = micro(2026, 11, 14)
        records = [
            row(1, 'attributeSubject', 'attribute', t=stamp, timestamp_semantics='examination_observation'),
            row(2, 'fileSeen', 'file', t=stamp,
                time_meaning='file observed when the image was examined; not application execution'),
            row(3, 'attributeSubject', 'attribute', t=stamp,
                time_meaning='when this source attribute was examined, not the described event'),
            row(4, 'usbInsert', 'unknown', t=stamp - 1000000),
            row(5, 'programRun', 'unknown', t=stamp - 1000000, time_meaning='unspecified record timestamp'),
            row(6, 'webVisit', 'page', t=stamp, time_meaning='browser history visit time'),
            row(7, 'fileRemoved', 'file', t=stamp + 1000000, timestamp_semantics='journal_observation'),
            row(8, 'lnkTarget', 'target.txt', t=stamp + 2000000, timestamp_semantics='destlist_entry_update'),
        ]
        info = brief.build({'findings': [finding('F1', records)]})
        self.assertEqual((info['counts']['records'], info['counts']['dated'], info['counts']['undated']), (8, 3, 5))
        self.assertEqual(info['range'], {'from': stamp, 'to': stamp + 2000000})
        self.assertEqual(info['days'][0]['events'][0]['one'], 'Shortcut target')
        observations = brief.build({'findings': [finding('F1', records[:5])]})
        self.assertIsNone(observations['busiest'])
        self.assertEqual(observations['days'], [])

    def test_a_selection_counts_its_own_findings_but_still_lists_every_exhibit(self):
        info = brief.build(bundle(), ids=['F2'])
        self.assertEqual((info['counts']['findings'], info['counts']['recorded'], info['counts']['records']), (1, 2, 2))
        self.assertEqual([(item['label'], item['records']) for item in info['exhibits']],
                         [('PC', 2), ('USB#2', 0), ('USB#10', 0)])
        self.assertEqual(info['exhibits'][1]['digests'][0]['value'], 'ab' * 16)

    def test_conflicting_copies_stay_apart_and_malformed_input_is_counted_as_nothing(self):
        changed = dict(USB, obj_text='SERIAL-OTHER')
        info = brief.build({'findings': [finding('F1', [USB, changed, USB, 'junk', None])]})
        self.assertEqual(info['counts']['records'], 2)
        for junk in (None, [], 'x', {'findings': 'x'}, {'findings': [{'status': 'verified', 'cited_facts': 5}]},
                     {'findings': [finding('F1', [{'id': 1, 'kind': 5, 't': 'soon', 'prov': 'x'}])]}):
            with self.subTest(junk=junk):
                built = brief.build(junk)
                self.assertEqual((built['counts']['dated'], built['exhibits'], built['days']), (0, [], []))


if __name__ == '__main__':
    unittest.main()
