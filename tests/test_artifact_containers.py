"""Validated containers use structural schemas, exact origins and bounded reads."""
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import struct
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from extractor import artifact_containers as ac
from extractor.store import Evidence
from tests.test_inventory import FS


def sqlite_bytes(statements):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'db'
        with sqlite3.connect(path) as db:
            db.executescript(statements)
        return path.read_bytes()


CHROME = 'CREATE TABLE urls (id INTEGER, url TEXT); CREATE TABLE visits (id INTEGER, url INTEGER, visit_time INTEGER);'
FIREFOX = 'CREATE TABLE moz_places (id INTEGER, url TEXT); CREATE TABLE moz_historyvisits (id INTEGER, place_id INTEGER, visit_date INTEGER);'
STICKY = 'CREATE TABLE Note (Id TEXT, Text TEXT, CreatedAt INTEGER, UpdatedAt INTEGER);' + ''.join(
    'CREATE TABLE ' + name + ' (Id TEXT);' for name in ('Media', 'Insight', 'User', 'Stroke'))


def message(entries, identifier=100):
    record_set = NS(number_of_entries=len(entries), get_entry=lambda index: entries[index])
    return NS(identifier=identifier, number_of_record_sets=1, get_record_set=lambda index: record_set)


def prop(property_id, raw, value_type=0x1F):
    return NS(entry_type=property_id, value_type=value_type, data=raw)


def legacy_index(location):
    data = bytearray(0x4000 + 256)
    signature = b'Client UrlCache MMF Ver 5.2'
    data[:len(signature)] = signature
    data[0x250] = 3
    struct.pack_into('<4sI', data, 0x4000, b'URL ', 2)
    struct.pack_into('<I', data, 0x4000 + 52, 104)
    raw = location.encode('cp1252') + b'\0'
    data[0x4000 + 104:0x4000 + 104 + len(raw)] = raw
    return bytes(data)


class Containers(unittest.TestCase):
    def setUp(self):
        self.fs = FS()
        self.target = NS(fs=self.fs, user_details=NS(all_with_home=lambda: []))
        self.ctx = {'common': {'image': 'case.E01', 'exhibit': 'DESKTOP', 'source_snapshot': 'base-volume',
                               'source_variant': 'primary', 'tool': 'test'}, 'examined_at': 123_000_000}
        self.ev = Evidence()

    def run_reader(self):
        ac.extract(self.ev, self.target, self.ctx)
        return [{'kind': kind, 'time': time, 'obj': obj, 'aux': aux, 'prov': json.loads(prov)}
                for kind, time, res, obj, aux, prov in self.ev.rows()]

    def attributes(self, rows):
        return [row for row in rows if row['kind'] == 'attributeTextValue']

    def test_browser_identity_and_path_share_hash_scoped_subject_and_examination_time(self):
        path = 'C:/Users/Alex/AppData/Local/Google/Chrome/User Data/Profile 8/History'
        raw = sqlite_bytes(CHROME)
        self.fs.add(path, data=raw)
        rows = self.run_reader()
        values = self.attributes(rows)
        self.assertEqual(len(values), 2)
        self.assertEqual({row['prov']['attribute_role'] for row in values},
                         {'browser.history.path', 'browser.history.browser'})
        self.assertEqual({json.loads(row['aux']) for row in values}, {'Google Chrome', path.replace('/', '\\')})
        subjects = [row['aux'] for row in rows if row['kind'] == 'attributeSubject']
        self.assertEqual(len(set(subjects)), 1)
        scope = json.loads(subjects[0])
        self.assertEqual(scope[1], ['case.E01', 'DESKTOP', 'base-volume', 'primary'])
        self.assertEqual(scope[-1], hashlib.sha256(raw).hexdigest())
        self.assertTrue(all(row['time'] == self.ctx['examined_at'] for row in rows))
        self.assertTrue(all(row['prov']['container_sha256'] == scope[-1] for row in rows))
        self.assertFalse(self.ev.problems)

    def test_format_and_layout_are_both_required_not_filename_or_sqlite_header(self):
        for raw in (b'SQLite format 3\0' + bytes(100), sqlite_bytes('CREATE TABLE unrelated (id INTEGER);'), sqlite_bytes(FIREFOX)):
            with self.subTest(length=len(raw)):
                self.setUp()
                self.fs.add('C:/Users/Alex/AppData/Local/Google/Chrome/User Data/Default/History', data=raw)
                self.assertEqual(self.run_reader(), [])
                self.assertTrue(self.ev.problems)
        self.setUp()
        self.fs.add('C:/Users/Alex/Documents/History', data=sqlite_bytes(CHROME))
        self.assertEqual(self.run_reader(), [])

    def test_modern_sticky_schema_and_firefox_schema_are_supported(self):
        self.fs.add('C:/Users/Alex/AppData/Local/Packages/Microsoft.MicrosoftStickyNotes_test/LocalState/plum.sqlite',
                    data=sqlite_bytes(STICKY))
        self.fs.add('C:/Users/Alex/AppData/Roaming/Mozilla/Firefox/Profiles/abc.default/places.sqlite',
                    data=sqlite_bytes(FIREFOX))
        roles = {row['prov']['attribute_role'] for row in self.attributes(self.run_reader())}
        self.assertEqual(roles, {'sticky_notes.container.path', 'browser.history.path', 'browser.history.browser'})
        self.assertFalse(self.ev.problems)

    def test_legacy_ie_requires_history_prefix_and_allocated_bounded_records(self):
        raw = legacy_index('Visited: person@https://example.test/')
        self.assertEqual(ac._legacy_history(raw)['history_records_validated'], 1)
        for invalid in (legacy_index('https://example.test/cache'), b'Client UrlCache MMF Ver 5.2',
                        raw[:0x250] + b'\x01' + raw[0x251:]):
            with self.subTest(length=len(invalid)), self.assertRaises(ValueError):
                ac._legacy_history(invalid)
        for root, child in (('C:/Documents and Settings/Pat/Local Settings/History/History.IE5', 'index.dat'),
                            ('C:/Users/Pat/AppData/Local/Microsoft/Windows/History/History.IE5',
                             'MSHist012020010120200102/index.dat')):
            with self.subTest(root=root):
                self.setUp()
                self.fs.add(root + '/' + child, data=raw)
                values = self.attributes(self.run_reader())
                self.assertEqual(len(values), 2)
                self.assertEqual({row['prov']['format'] for row in values}, {'ie_legacy_history'})
                self.assertFalse(self.ev.problems)

    def test_integer_size_subtypes_are_supported_but_boolean_sizes_are_not(self):
        class ParsedSize(int):
            pass
        path = 'C:/Users/Pat/AppData/Local/Google/Chrome/User Data/Default/History'
        raw = sqlite_bytes(CHROME)
        self.fs.add(path, data=raw, size=ParsedSize(len(raw)))
        self.assertEqual(len(self.attributes(self.run_reader())), 2)
        self.setUp()
        self.fs.add(path, data=raw, size=True)
        self.assertEqual(self.run_reader(), [])
        self.assertTrue(self.ev.problems)

    def test_ese_container_ids_accept_parser_integer_subclasses_but_not_flags(self):
        class ParsedInteger(int):
            pass
        for cid, accepted in ((ParsedInteger(2), True), (True, False)):
            with self.subTest(cid=cid):
                containers = NS(column_names=['ContainerId', 'Name', 'Directory'],
                                records=lambda: iter([{'ContainerId': cid, 'Name': 'History', 'Directory': 'folder'}]))
                history = NS(column_names=['EntryId', 'Url'], records=lambda: iter([]))
                db = NS(table=lambda name: containers if name == 'Containers' else history)
                with patch.dict('sys.modules', {'dissect.database.ese': NS(ESE=lambda stream: db)}):
                    if accepted:
                        self.assertEqual(ac._ese(b'source bytes')['history_container_ids'], ['2'])
                    else:
                        with self.assertRaises(ValueError):
                            ac._ese(b'source bytes')

    def test_unknown_scope_and_size_limits_fail_closed_with_health(self):
        path = 'C:/Users/Alex/AppData/Local/Google/Chrome/User Data/Default/History'
        self.fs.add(path, data=sqlite_bytes(CHROME))
        del self.ctx['common']['source_snapshot']
        self.assertEqual(self.run_reader(), [])
        self.assertEqual(self.fs.opened, [])
        self.assertTrue(self.ev.problems)
        self.setUp()
        self.fs.add(path, data=sqlite_bytes(CHROME))
        with patch.object(ac, 'MAX_FILE_BYTES', 8):
            self.assertEqual(self.run_reader(), [])
        self.assertEqual(self.fs.opened, [])
        self.assertTrue(self.ev.problems)

    def test_same_path_and_bytes_in_other_snapshot_gets_different_subject(self):
        path = 'C:/Users/Alex/AppData/Local/Google/Chrome/User Data/Default/History'
        self.fs.add(path, data=sqlite_bytes(CHROME))
        first = [row['aux'] for row in self.run_reader() if row['kind'] == 'attributeSubject']
        self.ev = Evidence()
        self.ctx['common']['source_snapshot'] = 'vss:AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE'
        second = [row['aux'] for row in self.run_reader() if row['kind'] == 'attributeSubject']
        self.assertNotEqual(first[0], second[0])
        self.assertEqual(json.loads(second[0])[1][2], 'vss:aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee')

    def test_parse_stream_refuses_out_of_bounds_and_looping_reads(self):
        stream = ac.ParseBytes(b'abc')
        for action in (lambda: stream.seek(4), lambda: stream.seek(-1), lambda: stream.read(4)):
            with self.assertRaises(ValueError):
                action()
        with patch.object(ac, 'MAX_PARSE_READS', 2):
            stream = ac.ParseBytes(b'abc')
            stream.read(1); stream.read(1)
            with self.assertRaises(ValueError):
                stream.read(1)

    def test_thumbcache_known_structures_validate_but_truncation_and_counts_do_not(self):
        try:
            import dissect.thumbcache
        except ImportError:
            self.skipTest('optional extraction parser unavailable')
        header = struct.pack('<4sIIIII', b'IMMM', 21, 0, 1, 1, 0)
        entry = b'12345678' + struct.pack('<I5I', 1, 0, 0, 0, 0, 0)
        result = ac._thumbcache(header + entry)
        self.assertEqual(result['records_validated'], 1)
        for raw in (header, header + entry[:-1], struct.pack('<4sIIIII', b'IMMM', 21, 0, 2, 1, 0) + entry):
            with self.subTest(length=len(raw)), self.assertRaises(Exception):
                ac._thumbcache(raw)
        body = struct.pack('<4sI8sIIII', b'CMMM', 56, b'12345678', 2, 2, 4, 0) + bytes(16) + b'x\0' + bytes(2) + b'data'
        raw = struct.pack('<4sIIIII', b'CMMM', 21, 0, 24, 80, 1) + body
        self.assertEqual(ac._thumbcache(raw)['records_validated'], 1)
        with self.assertRaises(Exception):
            ac._thumbcache(raw[:-1])

    def test_empty_hash_slot_keeps_bounds_and_records_residual_without_payload_claim(self):
        try:
            import dissect.thumbcache
        except ImportError:
            self.skipTest('optional extraction parser unavailable')
        payload = struct.pack('<4sI8sIIII', b'CMMM', 56, b'12345678', 2, 2, 4, 0) + bytes(16) + b'x\0' + bytes(2) + b'data'
        residual = b'residual'
        slot = struct.pack('<4sI8sIIII', b'CMMM', 48 + len(residual), bytes(8), 0, 0, 0, 0) + bytes(16) + residual
        def database(parts):
            return struct.pack('<4sIIIII', b'CMMM', 21, 2, 24, 24 + len(parts), 3) + parts
        result = ac._thumbcache(database(payload + slot + payload))
        self.assertEqual(result['records_validated'], 3)
        self.assertEqual(result['empty_slot_count'], 1)
        self.assertEqual(result['empty_slot_samples'], [{'byte_offset': 80, 'slot_bytes': 56,
            'uninterpreted_bytes': 8, 'uninterpreted_sha256': hashlib.sha256(residual).hexdigest()}])
        self.assertIn('residual bytes not interpreted', result['validation'])
        for change in ('nonzero_hash', 'nonzero_checksum', 'nonzero_declared_data', 'out_of_bounds'):
            bad = bytearray(slot)
            if change == 'nonzero_hash':
                bad[8] = 1
            elif change == 'nonzero_checksum':
                bad[32] = 1
            elif change == 'nonzero_declared_data':
                struct.pack_into('<I', bad, 24, 1)
            else:
                struct.pack_into('<I', bad, 4, 9999)
            with self.subTest(change=change), self.assertRaises(Exception):
                ac._thumbcache(database(payload + bad + payload))

    def test_virtual_alias_maps_only_by_unique_identical_filesystem_and_deduplicates(self):
        relative = 'Documents and Settings/LocalService/Local Settings/History/History.IE5/index.dat'
        raw = legacy_index('Visited: service@https://example.test/')
        self.fs.add('C:/' + relative, data=raw)
        self.fs.add('sysvol/' + relative, data=raw)
        self.fs.mounts['sysvol'] = self.fs.mounts['c:']
        home = self.fs.path('sysvol/Documents and Settings/LocalService')
        self.target.user_details = NS(all_with_home=lambda: [NS(home_path=home)])
        values = self.attributes(self.run_reader())
        self.assertEqual(len(values), 2)
        self.assertEqual({row['prov']['source_path'] for row in values}, {'C:\\' + relative.replace('/', '\\')})
        self.assertEqual(self.fs.opened, ['C:/' + relative])
        self.assertFalse(self.ev.problems)
        self.assertEqual(ac._windows_path(self.target, self.fs.path('/sysvol/' + relative)),
                         'C:\\' + relative.replace('/', '\\'))
        self.fs.mounts['d:'] = self.fs.mounts['c:']
        with self.assertRaises(ValueError):
            ac._windows_path(self.target, self.fs.path('/sysvol/' + relative))
        self.fs.mounts['sysvol'] = NS(ntfs=NS(serial=self.fs.mounts['c:'].ntfs.serial))
        with self.assertRaises(ValueError):
            ac._windows_path(self.target, self.fs.path('/sysvol/' + relative))

    def test_unmapped_virtual_path_is_a_health_issue_not_a_windows_path_answer(self):
        relative = 'Documents and Settings/Service/Local Settings/History/History.IE5/index.dat'
        self.fs.add('other-volume/' + relative, data=legacy_index('Visited: service@https://example.test/'))
        home = self.fs.path('other-volume/Documents and Settings/Service')
        self.target.user_details = NS(all_with_home=lambda: [NS(home_path=home)])
        self.assertEqual(self.run_reader(), [])
        self.assertEqual(self.fs.opened, [])
        self.assertTrue(self.ev.problems)

    def test_random_ole_signature_does_not_establish_sticky_subtype(self):
        try:
            import dissect.ole
        except ImportError:
            self.skipTest('optional extraction parser unavailable')
        with self.assertRaises(Exception):
            ac._sticky_ole(bytes.fromhex('d0cf11e0a1b11ae1') + bytes(504))

    def test_mail_store_handle_is_validated_once_reused_and_closed(self):
        item = message([prop(0x1000, 'body'.encode('utf-16-le'))])
        folder = NS(identifier=1, number_of_sub_messages=1, number_of_sub_folders=0,
                    get_sub_message=lambda index: item)
        calls = []
        box = NS(open_file_object=lambda stream: calls.append(('open', stream.read())),
                 get_message_store=lambda: object(), get_root_folder=lambda: folder,
                 close=lambda: calls.append(('close',)))
        pypff = NS(file=lambda: box, get_version=lambda: 'test parser')
        self.fs.add('C:/Users/Pat/Documents/Outlook Files/archive.pst', data=b'captured file bytes')
        with patch.dict('sys.modules', {'pypff': pypff}):
            values = self.attributes(self.run_reader())
        self.assertEqual(calls, [('open', b'captured file bytes'), ('close',)])
        self.assertEqual({row['prov']['attribute_role'] for row in values},
                         {'mail.store.path', 'mail.message.body_unicode'})
        self.assertFalse(self.ev.problems)


class UnicodeMail(unittest.TestCase):
    def test_empty_absent_malformed_wrong_type_and_duplicates_are_distinct(self):
        self.assertIsNone(ac._unicode_property(message([]), 0x1000))
        self.assertEqual(ac._unicode_property(message([prop(0x1000, b'\0\0')]), 0x1000)[0], '')
        self.assertEqual(ac._unicode_property(message([prop(0x1000, 'Line\r\n'.encode('utf-16-le'))]), 0x1000)[0], 'Line\r\n')
        for entries in ([prop(0x1000, b'x')], [prop(0x1000, b'\x00\xd8')],
                        [prop(0x1000, b'body', 0x1E)], [prop(0x1000, b'\0\0'), prop(0x1000, b'\0\0')]):
            with self.subTest(entries=entries), self.assertRaises(ValueError):
                ac._unicode_property(message(entries), 0x1000)

    def test_body_and_subject_share_exact_message_occurrence_and_empty_body_is_emitted(self):
        messages = [message([prop(0x0037, 'Subject'.encode('utf-16-le')), prop(0x1000, b'\0\0')], 7),
                    message([prop(0x0037, 'Subject'.encode('utf-16-le'))], 8)]
        folder = NS(identifier=1, number_of_sub_messages=2, number_of_sub_folders=0,
                    get_sub_message=lambda index: messages[index])
        box = NS(get_root_folder=lambda: folder)
        prov = {'image': 'image.E01', 'exhibit': 'PC', 'source_snapshot': 'base-volume', 'source_variant': 'primary',
                'artifact': 'mail.pst', 'source_path': 'mail.pst', 'container_sha256': 'a' * 64}
        ev = Evidence()
        ac.mail_fields(ev, box, 'scoped-container', prov, 123)
        rows = [json.loads(row[5]) for row in ev.rows() if row[0] == 'attributeTextValue']
        self.assertEqual([row['attribute_role'] for row in rows].count('mail.message.body_unicode'), 1)
        bodies = [row for row in ev.rows() if row[0] == 'attributeTextValue' and json.loads(row[5])['attribute_role'] == 'mail.message.body_unicode']
        self.assertEqual(json.loads(bodies[0][4]), '')
        subject_by_attribute = {row[3]: row[4] for row in ev.rows() if row[0] == 'attributeSubject'}
        first = [subject_by_attribute[row[3]] for row in ev.rows()
                 if row[0] == 'attributeTextValue' and json.loads(row[5])['message_locator']['pff_item_identifier'] == 7]
        self.assertEqual(len(first), 2)
        self.assertEqual(first[0], first[1])
        self.assertEqual(len(set(subject_by_attribute.values())), 2)
        self.assertFalse(ev.problems)

    def test_message_budget_and_bad_unicode_report_health_without_fabricated_body(self):
        item = message([prop(0x1000, b'x')])
        folder = NS(identifier=1, number_of_sub_messages=1, number_of_sub_folders=0, get_sub_message=lambda index: item)
        box = NS(get_root_folder=lambda: folder)
        prov = {'artifact': 'mail.pst', 'source_path': 'mail.pst'}
        ev = Evidence()
        ac.mail_fields(ev, box, 'container', prov, 123)
        self.assertEqual(ev.rows(), [])
        self.assertTrue(ev.problems)
        ev = Evidence()
        with patch.object(ac, 'MAX_RECORDS', 0):
            ac.mail_fields(ev, box, 'container', prov, 123)
        self.assertEqual(ev.rows(), [])
        self.assertTrue(ev.problems)


if __name__ == '__main__':
    unittest.main()
