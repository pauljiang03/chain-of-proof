"""Windows instance observations never stand in for validated hardware serials."""
from datetime import datetime, timezone
import hashlib
import io
import json
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

from extractor import windows
from extractor.source_scope import base_volume_scope
from extractor.store import Evidence, us
from extractor.tags import add_tags


EXAMINED = 1800000000123456
STAMP = datetime(2015, 3, 25, tzinfo=timezone.utc)
DEVICE = 'Disk&Ven_Example&Prod_Storage&Rev_1.00'
IDS = ('6&AAAA1111&0&1', '6&BBBB2222&0&2')


def scope(**specific):
    return dict(dict(base_volume_scope(), image='synthetic.E01', exhibit='PC'), **specific)


def registry(*instances, stamp=STAMP, device=DEVICE):
    children = [NS(name=name, timestamp=stamp) for name in instances]
    dev = NS(name=device, subkeys=lambda: children)
    root = NS(subkeys=lambda: [dev])
    return NS(registry=NS(key=lambda path: root))


def section(instance=IDS[0], stamp='2015/03/25 12:34:56.789'):
    return (f'>>>  [Device Install (Hardware initiated) - USBSTOR\\{DEVICE}\\{instance}]\r\n'
            f'>>>  Section start {stamp}\r\n')


def log_target(raw):
    file = NS(exists=lambda: True, open=lambda mode: io.BytesIO(raw))
    return NS(fs=NS(path=lambda path: file))


def observations(ev):
    subjects = {row[3]: row[4] for row in ev.rows() if row[0] == 'attributeSubject'}
    out = {}
    for row in ev.rows():
        if row[0] != 'attributeTextValue':
            continue
        prov = json.loads(row[5])
        subject = subjects[row[3]]
        item = out.setdefault(subject, {'fields': {}, 'provenance': prov})
        item['fields'][prov['attribute_role']] = json.loads(row[4])
    return list(out.values())


class UsbInstanceIdentity(unittest.TestCase):
    def test_registry_audit_counterexample_preserves_two_complete_instances(self):
        ev = Evidence()
        self.assertEqual(windows._usb(ev, registry(*IDS), scope(), examined_at=EXAMINED), 2)
        self.assertEqual(ev.problems, [])
        rows = observations(ev)
        self.assertEqual(len(rows), 2)
        self.assertEqual({r['fields']['usb.instance_id'] for r in rows}, set(IDS))
        self.assertEqual({r['fields']['usb.device_instance_id'] for r in rows},
                         {'USBSTOR\\' + DEVICE + '\\' + instance for instance in IDS})
        self.assertTrue(all(r['fields']['usb.device_id'] == 'USBSTOR\\' + DEVICE for r in rows))
        self.assertTrue(all(r['fields']['usb.recorded_time'] == STAMP.isoformat() for r in rows))
        self.assertTrue(all(r['provenance']['source_variant'] == 'unknown' for r in rows))
        self.assertTrue(all(r['provenance']['device_identity_kind'] == 'windows_device_instance' for r in rows))
        self.assertTrue(all(row[1] == EXAMINED for row in ev.rows()))
        self.assertFalse(any(row[0] == 'usbInsert' for row in ev.rows()))

    def test_serial_looking_identifiers_are_not_promoted_or_truncated(self):
        ev = Evidence()
        windows._usb(ev, registry('REALLOOKING123&0', 'NoAmpersandSerial'), scope(), examined_at=EXAMINED)
        self.assertEqual({r['fields']['usb.instance_id'] for r in observations(ev)},
                         {'REALLOOKING123&0', 'NoAmpersandSerial'})
        add_tags(ev, EXAMINED, policy={'authorized_device_serials': ['6', 'REALLOOKING123'],
                                    'authorized_device_serials_complete': True})
        self.assertFalse(any(row[0] in ('usbInsert', 'tag') for row in ev.rows()))

    def test_native_text_subclass_is_retained_without_using_coercion(self):
        class NativeText(str):
            def __str__(self):
                return 'wrong string override'
        ev = Evidence()
        windows._usb(ev, registry(NativeText(IDS[0]), device=NativeText(DEVICE)), scope(), examined_at=EXAMINED)
        self.assertEqual(observations(ev)[0]['fields']['usb.instance_id'], IDS[0])

    def test_registry_subject_scope_and_source_occurrence_prevent_merging(self):
        ev = Evidence()
        for change in ({}, {'image': 'other.E01'}, {'exhibit': 'OTHER'},
                       {'source_snapshot': 'vss:00000000-0000-0000-0000-000000000001'}):
            windows._usb(ev, registry(IDS[0], IDS[0]), scope(**change), examined_at=EXAMINED)
        self.assertEqual(len(observations(ev)), 8)
        # Unknown physical hive identity is preserved even if the caller says primary.
        self.assertEqual({r['provenance']['source_variant'] for r in observations(ev)}, {'unknown'})

    def test_invalid_components_are_reported_without_losing_other_records(self):
        for invalid in (6, b'6', '', 'bad\\component', 'bad\x00component', 'bad\ncomponent'):
            with self.subTest(invalid=invalid):
                ev = Evidence()
                windows._usb(ev, registry(invalid, IDS[0]), scope(), examined_at=EXAMINED)
                self.assertEqual(len(observations(ev)), 1)
                self.assertTrue(ev.problems)

    def test_unknown_registry_time_keeps_identity_but_never_invents_event_time(self):
        ev = Evidence()
        windows._usb(ev, registry(IDS[0], stamp=datetime(2015, 3, 25)), scope(), examined_at=EXAMINED)
        row, = observations(ev)
        self.assertNotIn('usb.recorded_time', row['fields'])
        self.assertTrue(ev.problems)
        self.assertTrue(all(row[1] == EXAMINED for row in ev.rows()))

    def test_explicit_examination_time_and_source_identity_required(self):
        for examined in (None, 0, True, -1, '1800000000123456'):
            ev = Evidence()
            windows._usb(ev, registry(IDS[0]), scope(), examined_at=examined)
            self.assertEqual(ev.rows(), [])
            self.assertTrue(ev.problems)
        for common in ({'image': 'x'}, {'exhibit': 'x'}, scope(image=' ')):
            ev = Evidence()
            windows._setupapi(ev, log_target(section().encode()), common, examined_at=EXAMINED)
            self.assertEqual(ev.rows(), [])
            self.assertTrue(ev.problems)

    def test_setupapi_retains_distinct_ids_and_local_time_without_current_zone_conversion(self):
        ev = Evidence()
        raw = ''.join(section(instance) for instance in IDS).encode()
        windows._setupapi(ev, log_target(raw), scope(), 'invalid/zone', examined_at=EXAMINED)
        self.assertEqual(ev.problems, [])
        rows = observations(ev)
        self.assertEqual({r['fields']['usb.instance_id'] for r in rows}, set(IDS))
        self.assertTrue(all(r['fields']['usb.recorded_time'] == '2015/03/25 12:34:56.789' for r in rows))
        self.assertTrue(all('UTC offset not recorded' in r['fields']['usb.record_time_meaning'] for r in rows))
        self.assertTrue(all(r['provenance']['timestamp_semantics'] == 'examination_observation' for r in rows))
        self.assertFalse(any(row[0] == 'usbInsert' for row in ev.rows()))

    def test_setupapi_dst_fold_cannot_supply_the_audited_false_utc_ordering(self):
        # Exact audit source: the two valid interpretations straddle 06:00 UTC.
        raw = (b'>>> [Device Install (Hardware initiated) - USBSTOR\\DiskFixture\\DEVICEA]\n'
               b'>>> Section start 2026/11/01 01:30:00.000\n')
        wall = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo('America/New_York'))
        alternatives = [wall.replace(fold=fold).astimezone(timezone.utc) for fold in (0, 1)]
        reference = datetime(2026, 11, 1, 6, 0, tzinfo=timezone.utc)
        self.assertEqual([stamp.isoformat() for stamp in alternatives],
                         ['2026-11-01T05:30:00+00:00', '2026-11-01T06:30:00+00:00'])
        self.assertLess(alternatives[0], reference)
        self.assertGreater(alternatives[1], reference)
        ev = Evidence()
        windows._setupapi(ev, log_target(raw), scope(), 'America/New_York', examined_at=EXAMINED)
        row, = observations(ev)
        self.assertEqual(row['fields']['usb.recorded_time'], '2026/11/01 01:30:00.000')
        self.assertIn('UTC offset not recorded', row['fields']['usb.record_time_meaning'])
        self.assertEqual(ev.problems, [])
        # No resolved event row exists for the audit's usbInsert-before claim.
        self.assertFalse(any(item[0] == 'usbInsert' for item in ev.rows()))
        self.assertTrue(all(item[1] == EXAMINED for item in ev.rows()))
        self.assertTrue(all(item[1] not in {us(stamp) for stamp in alternatives} for item in ev.rows()))
        self.assertTrue(all(json.loads(item[-1])['timestamp_semantics'] == 'examination_observation'
                            for item in ev.rows()))

    def test_setupapi_dst_gap_is_retained_as_text_without_inventing_a_utc_instant(self):
        # 02:30 does not occur in New York on this date. The log has no offset;
        # retain its literal text without claiming that this was the source zone.
        ev = Evidence()
        windows._setupapi(ev, log_target(section(stamp='2026/03/08 02:30:00.000').encode()),
                          scope(), 'America/New_York', examined_at=EXAMINED)
        row, = observations(ev)
        self.assertEqual(row['fields']['usb.recorded_time'], '2026/03/08 02:30:00.000')
        self.assertIn('UTC offset not recorded', row['fields']['usb.record_time_meaning'])
        self.assertFalse(any(item[0] == 'usbInsert' for item in ev.rows()))
        self.assertTrue(all(item[1] == EXAMINED for item in ev.rows()))
        self.assertEqual(ev.problems, [])

    def test_setupapi_repeated_sections_are_distinct_source_occurrences(self):
        ev = Evidence()
        first = section().encode()
        raw = first * 2
        windows._setupapi(ev, log_target(raw), scope(), examined_at=EXAMINED)
        rows = observations(ev)
        self.assertEqual(len(rows), 2)
        locators = [r['provenance']['source_entry'] for r in rows]
        self.assertEqual({p['header_line'] for p in locators}, {1, 3})
        self.assertEqual({p['byte_offset'] for p in locators}, {0, len(first)})
        self.assertEqual({p['source_sha256'] for p in locators}, {hashlib.sha256(raw).hexdigest()})
        for p in locators:
            self.assertEqual(raw[p['byte_offset']:p['byte_offset'] + p['byte_length']], first)

    def test_setupapi_byte_locators_include_bom_and_multibyte_prefix_correctly(self):
        for encoding, bom in (('utf-8', b'\xef\xbb\xbf'), ('utf-16-le', b'\xff\xfe'),
                              ('utf-16-be', b'\xfe\xff')):
            with self.subTest(encoding=encoding):
                prefix = 'unrelated text \u03a9\r\n'
                raw = bom + (prefix + section()).encode(encoding)
                ev = Evidence()
                windows._setupapi(ev, log_target(raw), scope(), examined_at=EXAMINED)
                row, = observations(ev)
                loc = row['provenance']['source_entry']
                self.assertEqual(loc['byte_offset'], len(bom + prefix.encode(encoding)))
                self.assertEqual(raw[loc['byte_offset']:loc['byte_offset'] + loc['byte_length']],
                                 section().encode(encoding))
                self.assertEqual(loc['header_line'], 2)
                self.assertEqual(ev.problems, [])

    def test_setupapi_changed_bytes_do_not_reuse_an_observation_subject(self):
        ev = Evidence()
        for raw in (section().encode(), (section() + 'unrelated footer\r\n').encode()):
            windows._setupapi(ev, log_target(raw), scope(), examined_at=EXAMINED)
        self.assertEqual(len(observations(ev)), 2)

    def test_setupapi_invalid_decoding_never_replaces_identifier_bytes(self):
        ev = Evidence()
        raw = section('bad\ufffdid').encode().replace('\ufffd'.encode(), b'\xff')
        windows._setupapi(ev, log_target(raw + section().encode()), scope(), examined_at=EXAMINED)
        row, = observations(ev)
        self.assertEqual(row['fields']['usb.instance_id'], IDS[0])
        self.assertTrue(ev.problems)
        ev = Evidence()
        with self.assertRaises(UnicodeDecodeError):
            windows._setupapi(ev, log_target(b'\xef\xbb\xbf' + raw), scope(), examined_at=EXAMINED)
        self.assertEqual(ev.rows(), [])

    def test_setupapi_unrelated_ansi_text_does_not_erase_ascii_identifiers(self):
        ev = Evidence()
        prefix = b'dvi: C:\\Users\\Andr\xe9\\Driver.inf\r\n'
        windows._setupapi(ev, log_target(prefix + section().encode()), scope(), examined_at=EXAMINED)
        row, = observations(ev)
        self.assertEqual(row['fields']['usb.instance_id'], IDS[0])
        self.assertEqual(row['provenance']['source_entry']['byte_offset'], len(prefix))
        self.assertEqual(ev.problems, [])

    def test_ansi_non_newline_byte_cannot_create_a_section_boundary(self):
        ev = Evidence()
        raw = b'unrelated ANSI text\x85' + section().encode()
        windows._setupapi(ev, log_target(raw), scope(), examined_at=EXAMINED)
        self.assertEqual(ev.rows(), [])

    def test_setupapi_invalid_or_missing_timestamp_retains_only_identifier_observation(self):
        for raw in (section(stamp='2015/99/25 12:34:56.789').encode(),
                    section().splitlines()[0].encode()):
            ev = Evidence()
            windows._setupapi(ev, log_target(raw), scope(), examined_at=EXAMINED)
            row, = observations(ev)
            self.assertNotIn('usb.recorded_time', row['fields'])
            self.assertTrue(ev.problems)

    def test_reader_caps_are_reported_without_completeness_claims(self):
        with patch.object(windows, 'MAX_USB_RECORDS', 1):
            ev = Evidence()
            self.assertEqual(windows._usb(ev, registry(*IDS), scope(), examined_at=EXAMINED), 1)
            self.assertEqual(len(observations(ev)), 1)
            self.assertTrue(ev.problems)
            ev = Evidence()
            self.assertEqual(windows._setupapi(ev, log_target((section() * 2).encode()), scope(),
                                             examined_at=EXAMINED), 1)
            self.assertEqual(len(observations(ev)), 1)
            self.assertTrue(ev.problems)
        with patch.object(windows, 'MAX_SETUPAPI_BYTES', 16), self.assertRaises(ValueError):
            windows._setupapi(Evidence(), log_target(section().encode()), scope(), examined_at=EXAMINED)


if __name__ == '__main__':
    unittest.main()
