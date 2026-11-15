"""Source fixtures for full search tuples and strict modern Recycle Bin indexes."""
from datetime import datetime, timezone
import io
import json
import struct
from types import SimpleNamespace as NS
import unittest

from extractor import windows as w
from extractor.store import Evidence

EXAMINED = 1800000000123456
WHEN = datetime(2020, 2, 3, 4, 5, 6, tzinfo=timezone.utc)
COMMON = dict(image='arbitrary.E01', exhibit='OTHER-PC',
              source_snapshot='base-volume', source_variant='primary')
FT = 132251763061234567


def attrs(ev):
    return [(json.loads(row[-1])['attribute_role'], json.loads(row[4]), json.loads(row[-1]))
            for row in ev.rows() if row[0] == 'attributeTextValue']


def search_record(**changes):
    data = dict(source='D:/Users/A/History', id=71, browser='chrome', ts=WHEN,
                url='https://www.google.com/search?q=C%2B%2B+%2520', username='A')
    data.update(changes)
    return NS(**data)


def index(version=1, original=r'E:\Folder\literal.txt', ft=FT):
    raw = (original + '\0').encode('utf-16-le')
    head = struct.pack('<QQQ', version, 1234, ft)
    return head + (raw.ljust(520, b'\0') if version == 1
                   else struct.pack('<I', len(raw) // 2) + raw)


def mft_record(data, segment=12, sequence=4, flags=1, name='$IABC123.txt'):
    return NS(filename=name, segment=segment,
              header=NS(SequenceNumber=sequence, Flags=flags), open=lambda: io.BytesIO(data))


class SearchFields(unittest.TestCase):
    def run_records(self, records):
        ev = Evidence()
        target = NS(browser=NS(history=lambda: records), has_function=lambda _: True)
        count = w._searches(ev, target, COMMON, examined_at=EXAMINED)
        return ev, count

    def test_decode_once_and_preserve_full_url_and_keyword_spacing(self):
        url = 'https://www.google.com/search?q=+C%2B%2B+%2520+' + '&retained=' + 'x' * 500
        ev, count = self.run_records([search_record(url=url)])
        values = {role: value for role, value, _ in attrs(ev)}
        self.assertEqual(ev.problems, [])
        self.assertEqual(count, 1)
        self.assertEqual(values['browser.search.url'], url)
        self.assertEqual(values['browser.search.query'], ' C++ %20 ')
        self.assertEqual(values['browser.search.recorded_time'], '2020-02-03T04:05:06Z')
        legacy = next(row for row in ev.rows() if row[0] == 'webSearch')
        self.assertEqual(legacy[3], ' C++ %20 ')
        self.assertEqual(json.loads(legacy[-1])['url'], url)
        self.assertEqual(len({row[4] for row in ev.rows() if row[0] == 'attributeSubject'}), 1)
        self.assertTrue(all(row[1] == EXAMINED for row in ev.rows() if row[0] != 'webSearch'))

    def test_supported_hosts_not_substrings_credentials_or_other_schemes(self):
        for url in ('https://google.com.evil.test/?q=x', 'https://fakegoogle.com/?q=x',
                    'https://google.com@evil.test/?q=x', 'https://evil@google.com/?q=x',
                    'file://google.com/?q=x', 'https://example.org/?q=x'):
            with self.subTest(url=url):
                self.assertIsNone(w.search_query(url))
        self.assertEqual(w.search_query('https://www.google.co.uk/?q=hello')[0], 'hello')
        for url in ('https://google.com/url?q=https%3A%2F%2Fexample.org',
                    'https://mail.yahoo.com/?p=mailbox', 'https://unreviewed.google.com/?q=x'):
            self.assertIsNone(w.search_query(url))

    def test_google_fragment_is_distinct_from_other_provider_fragment(self):
        self.assertEqual(w.search_query('https://google.com/?q=old#q=new%2B')[0], 'new+')
        self.assertEqual(w.search_query('https://bing.com/?q=old#q=new')[0], 'old')
        self.assertIsNone(w.search_query('https://google.com/?q=old#q='))

    def test_ambiguous_invalid_and_oversize_queries_are_refused(self):
        for url in ('https://google.com/?q=a&q=b', 'https://google.com/?q=%FF',
                    'https://google.com/?q=%Q0', 'https://google.com/?q=%00',
                    'https://google.com/?q=a\nb', 'https://google.com/?q=' + 'x' * w.MAX_SEARCH_URL):
            with self.subTest(url=url[:50]), self.assertRaises(ValueError):
                w.search_query(url)

    def test_bad_history_record_does_not_hide_later_valid_record(self):
        ev, count = self.run_records([search_record(ts=WHEN.replace(tzinfo=None)), search_record(id=72)])
        self.assertEqual(count, 1)
        self.assertEqual(len(ev.problems), 1)
        self.assertEqual(len(attrs(ev)), 4)

    def test_missing_locator_retains_legacy_but_no_typed_tuple(self):
        ev, count = self.run_records([search_record(id=None)])
        self.assertEqual(count, 1)
        self.assertEqual(attrs(ev), [])
        self.assertEqual(len(ev.problems), 1)

    def test_different_record_values_and_source_axes_do_not_join(self):
        ev, _ = self.run_records([search_record(), search_record(url='https://google.com/?q=other')])
        self.assertEqual(len({r[4] for r in ev.rows() if r[0] == 'attributeSubject'}), 2)
        target = NS(browser=NS(history=lambda: [search_record()]), has_function=lambda _: True)
        w._searches(ev, target, dict(COMMON, source_snapshot='vss:11111111-1111-1111-1111-111111111111'),
                    examined_at=EXAMINED)
        self.assertEqual(len({r[4] for r in ev.rows() if r[0] == 'attributeSubject'}), 3)


class RecycleIndexFields(unittest.TestCase):
    def test_both_versions_keep_drive_unicode_and_source_time_precision(self):
        for version in (1, 2):
            result = w.parse_recycle_index(index(version, r'E:\Other\café.txt'))
            self.assertEqual(result['original_path'], r'E:\Other\café.txt')
            self.assertEqual(result['filetime'], FT)
            self.assertTrue(result['deleted_at'].endswith('.1234567Z'))
            self.assertEqual(result['path_byte_offset'], 24 if version == 1 else 28)

    def test_long_version_two_path_is_not_truncated_at_old_1100_byte_limit(self):
        original = 'F:\\' + 'a' * 1200 + '.txt'
        result = w.parse_recycle_index(index(2, original))
        self.assertEqual(result['original_path'], original)

    def test_truncation_invalid_lengths_terminators_and_unicode_refuse(self):
        good = index(2)
        corrupt_count = bytearray(good)
        struct.pack_into('<I', corrupt_count, 24, 900)
        invalid_unicode = bytearray(good)
        invalid_unicode[28:30] = b'\x00\xd8'
        samples = [index()[:-1], index() + b'x', good[:-1], good + b'\0\0',
                   bytes(corrupt_count), bytes(invalid_unicode), good[:-2] + b'xx',
                   index(2, 'relative.txt'), index(ft=0), index(2, 'E:\\a\0b')]
        for data in samples:
            with self.subTest(length=len(data)), self.assertRaises(ValueError):
                w.parse_recycle_index(data)

    def test_tuple_exact_mft_subject_alias_dedup_and_no_bin_emptying_inference(self):
        class SourceString(str):
            pass
        rec = mft_record(index(), flags=0, name=SourceString('$IABC123.txt'))
        fs = NS(ntfs=NS(serial=0x12345678, mft=NS(segments=lambda: [rec])))
        target = NS(fs=NS(mounts={'d:': fs, 'sysvol': fs, 'e:': fs}))
        ev = Evidence()
        self.assertEqual(w._recycle_bin(ev, target, COMMON, examined_at=EXAMINED), 1)
        self.assertEqual(ev.problems, [])
        fields = {role: value for role, value, _ in attrs(ev)}
        self.assertEqual(fields['recycle.original_path'], r'E:\Folder\literal.txt')
        self.assertEqual(fields['recycle.index_file_name'], '$IABC123.txt')
        self.assertEqual(len({r[4] for r in ev.rows() if r[0] == 'attributeSubject'}), 1)
        for _, _, prov in attrs(ev):
            self.assertEqual(prov['mft_segment'], 12)
            self.assertEqual(prov['mft_sequence_number'], 4)
            self.assertFalse(prov['index_record_in_use'])
            self.assertEqual(prov['source_variant'], 'unallocated-recovery')
            self.assertNotIn('note', prov)
            self.assertEqual(prov['source_path'], r'D:\$MFT')

    def test_bad_index_does_not_hide_valid_one_or_other_filesystem(self):
        bad, good = mft_record(index()[:40]), mft_record(index(2), segment=13)
        first = NS(ntfs=NS(serial=1, mft=NS(segments=lambda: [bad, good])))
        second = NS(ntfs=NS(serial=1, mft=NS(segments=lambda: [good])))
        ev = Evidence()
        target = NS(fs=NS(mounts={'c:': first, 'f:': second}))
        self.assertEqual(w._recycle_bin(ev, target, COMMON, examined_at=EXAMINED), 2)
        self.assertEqual(len(ev.problems), 1)
        self.assertEqual(len({r[4] for r in ev.rows() if r[0] == 'attributeSubject'}), 2)

    def test_missing_examination_time_keeps_legacy_without_inventing_typed_time(self):
        rec = mft_record(index())
        fs = NS(ntfs=NS(serial=1, mft=NS(segments=lambda: [rec])))
        ev = Evidence()
        target = NS(fs=NS(mounts={'c:': fs}), browser=NS(history=lambda: [search_record()]))
        self.assertEqual(w._recycle_bin(ev, target, COMMON), 1)
        self.assertEqual(w._searches(ev, target, COMMON), 1)
        self.assertEqual(attrs(ev), [])
        self.assertEqual(len(ev.problems), 2)


if __name__ == '__main__':
    unittest.main()
