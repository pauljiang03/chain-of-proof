"""Synthetic PE/registry fixtures; no case images, answer keys, or execution."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from checker.catalog import decode_value
from extractor import application_identity as app
from extractor.store import Evidence


def node(key, value=b'', kind=1, children=()):
    data = bytearray(b'\0' * 6 + (key + '\0').encode('utf-16-le'))
    data.extend(b'\0' * (-len(data) % 4))
    data.extend(value)
    for child in children:
        data.extend(b'\0' * (-len(data) % 4))
        data.extend(child)
    struct.pack_into('<HHH', data, 0, len(data), len(value) // 2 if kind else len(value), kind)
    return bytes(data)


def version(tables=None):
    if tables is None:
        tables = [('040904b0', [('ProductName', 'Another Mail Product'), ('ProductVersion', '7.8 beta'),
                               ('FileDescription', ' A literal description '), ('FileVersion', '7.8.9.10')])]
    children = [node(label, children=[node(key, (value + '\0').encode('utf-16-le')) for key, value in fields])
                for label, fields in tables]
    fixed = struct.pack('<13I', 0xFEEF04BD, 0x10000, 0x630000, 1, 0x630000, 2, 0, 0, 0, 0, 0, 0, 0)
    return node('VS_VERSION_INFO', fixed, kind=0, children=[node('StringFileInfo', children=children)])


def pe(resource=None, *, pe64=False):
    resource = version() if resource is None else resource
    payload_at = 88
    resource_size = payload_at + len(resource)
    raw_size = (resource_size + 511) & ~511
    data = bytearray(0x200 + raw_size)
    data[:2] = b'MZ'
    struct.pack_into('<I', data, 0x3c, 0x80)
    data[0x80:0x84] = b'PE\0\0'
    optional_size = 240 if pe64 else 224
    struct.pack_into('<HHIIIHH', data, 0x84, 0x8664 if pe64 else 0x14c, 1, 0, 0, 0, optional_size, 2)
    optional = 0x98
    struct.pack_into('<H', data, optional, 0x20b if pe64 else 0x10b)
    struct.pack_into('<I', data, optional + 60, 0x200)
    directory = 112 if pe64 else 96
    struct.pack_into('<I', data, optional + directory - 4, 16)
    struct.pack_into('<II', data, optional + directory + 16, 0x1000, resource_size)
    section = optional + optional_size
    data[section:section + 8] = b'.rsrc\0\0\0'
    struct.pack_into('<IIII', data, section + 8, resource_size, 0x1000, raw_size, 0x200)
    base = 0x200
    for at in (0, 24, 48):
        struct.pack_into('<HH', data, base + at + 12, 0, 1)
    struct.pack_into('<II', data, base + 16, 16, 0x80000000 | 24)
    struct.pack_into('<II', data, base + 40, 1, 0x80000000 | 48)
    struct.pack_into('<II', data, base + 64, 1033, 72)
    struct.pack_into('<IIII', data, base + 72, 0x1000 + payload_at, len(resource), 1200, 0)
    data[base + payload_at:base + payload_at + len(resource)] = resource
    return data


class VersionParsing(unittest.TestCase):
    def test_literal_fields_and_exact_physical_bytes_in_pe32_and_pe64(self):
        for is64 in (False, True):
            with self.subTest(pe64=is64):
                data = pe(pe64=is64)
                resource, = app.version_resources(data)
                fields = app.version_strings(resource['data'])
                self.assertEqual([f['value'] for f in fields],
                                 ['Another Mail Product', '7.8 beta', ' A literal description ', '7.8.9.10'])
                for field in fields:
                    start = resource['byte_offset'] + field['value_offset']
                    self.assertEqual(data[start:start + field['value_byte_length']].hex(), field['raw_value_hex'])
                self.assertEqual(resource['resource_language'], 1033)
                self.assertEqual(fields[0]['string_table'], '040904b0')

    def test_language_tables_remain_separate_and_empty_text_is_literal(self):
        value = version([('040904b0', [('ProductName', 'Different')]),
                         ('041104b0', [('ProductName', '別の製品'), ('ProductVersion', '')])])
        rows = app.version_strings(value)
        self.assertEqual([r['value'] for r in rows], ['Different', '別の製品', ''])
        self.assertNotEqual(rows[0]['table_offset'], rows[1]['table_offset'])

    def test_fixed_numeric_version_is_not_substituted_for_absent_literal_string(self):
        self.assertEqual(app.version_strings(version([])), [])
        unrelated = node('VS_VERSION_INFO', kind=0, children=[
            node('VarFileInfo', children=[node('ProductName', 'not identity\0'.encode('utf-16-le'))])])
        self.assertEqual(app.version_strings(unrelated), [])

    def test_duplicate_keys_and_nontext_identity_are_rejected(self):
        duplicate = version([('040904b0', [('ProductName', 'A'), ('ProductName', 'B')])])
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            app.version_strings(duplicate)
        wrong_type = node('VS_VERSION_INFO', kind=0, children=[node('StringFileInfo', children=[
            node('040904b0', children=[node('ProductName', b'1234', kind=0)])])])
        with self.assertRaisesRegex(ValueError, 'text leaf'):
            app.version_strings(wrong_type)

    def test_unterminated_keys_values_and_child_lengths_are_bounded(self):
        invalid = bytearray(version())
        fields = app.version_strings(invalid)
        at = fields[0]['field_offset']
        cases = []
        broken = bytearray(invalid)
        struct.pack_into('<H', broken, at, 0xffff)
        cases.append(broken)
        broken = bytearray(invalid)
        struct.pack_into('<H', broken, at + 2, 0xffff)
        cases.append(broken)
        broken = bytearray(invalid)
        value_end = fields[0]['value_offset'] + fields[0]['value_byte_length']
        broken[value_end - 2:value_end] = b'XX'
        cases.append(broken)
        cases.append(b'\x08\0\0\0\x01\0XX')
        for data in cases:
            with self.subTest(data_length=len(data)), self.assertRaises(ValueError):
                app.version_strings(data)

    def test_pe_resource_cycles_invalid_rvas_and_truncation_are_refused(self):
        original = pe()
        cases = [original[:63], original[:-1]]
        bad = bytearray(original)
        struct.pack_into('<I', bad, 0x214, 0x80000000)
        cases.append(bad)
        bad = bytearray(original)
        struct.pack_into('<I', bad, 0x248, 0x200000)
        cases.append(bad)
        bad = bytearray(original)
        struct.pack_into('<I', bad, 0x3c, 0xffffff00)
        cases.append(bad)
        for data in cases:
            with self.subTest(data_length=len(data)), self.assertRaises(ValueError):
                app.version_resources(data)

    def test_overlapping_sections_do_not_select_an_arbitrary_byte_source(self):
        data = pe()
        struct.pack_into('<H', data, 0x86, 2)
        data[0x1a0:0x1c8] = data[0x178:0x1a0]
        with self.assertRaisesRegex(ValueError, 'ambiguous'):
            app.version_resources(data)

    def test_limits_and_missing_resource_are_explicit(self):
        with patch.object(app, 'MAX_RESOURCE_ENTRIES', 0), self.assertRaisesRegex(ValueError, 'limit'):
            app.version_resources(pe())
        with patch.object(app, 'MAX_VERSION_NODES', 1), self.assertRaisesRegex(ValueError, 'limit'):
            app.version_strings(version())
        data = pe()
        struct.pack_into('<II', data, 0x98 + 96 + 16, 0, 0)
        self.assertEqual(app.version_resources(data), [])


class RegisteredIdentity(unittest.TestCase):
    def test_registry_selection_uses_live_default_values_and_preserves_source(self):
        def entry(path, values):
            return SimpleNamespace(path=path, name=path.rsplit('\\', 1)[-1],
                                   values=lambda: [SimpleNamespace(name=k, value=v) for k, v in values.items()])
        machine = SimpleNamespace(name='SOFTWARE', backup=False, sid=None, path='SYSTEM-HIVE')
        backup = SimpleNamespace(name='SOFTWARE', backup=True, sid=None, path='BACKUP-HIVE')
        user = SimpleNamespace(name='USER', backup=False, sid='S-1-5-OTHER', path='USER-HIVE')
        machine_entry = entry(app.APP_PATHS + '\\chosen.exe', {'(Default)': 'D:\\Apps\\actual.exe',
                                                               'Path': 'D:\\DoNotEnumerate'})
        user_entry = entry('Software\\' + app.APP_PATHS + '\\other.exe', {'': 'E:\\Tools\\different.exe'})
        visited = []
        def open_key(ev, hive, path):
            visited.append((hive.path, path))
            entries = ([machine_entry] if hive is machine and path == app.APP_PATHS else
                       [user_entry] if hive is user else [])
            return SimpleNamespace(subkeys=lambda: entries)
        target = SimpleNamespace()
        ev = Evidence()
        with patch('extractor.system._hives', return_value=[machine, backup, user]), patch('extractor.system._open', side_effect=open_key):
            rows = list(app._registered(ev, target))
        self.assertEqual([path for path, _ in rows], ['D:\\Apps\\actual.exe', 'E:\\Tools\\different.exe'])
        self.assertNotIn('BACKUP-HIVE', [hive for hive, _ in visited])
        self.assertEqual(rows[1][1]['account_sid'], 'S-1-5-OTHER')
        self.assertEqual(rows[0][1]['registry_key'], machine_entry.path)
        self.assertEqual(ev.problems, [])

    def test_registration_is_literal_and_never_a_path_search_or_command(self):
        target = SimpleNamespace(expand_env=lambda raw, sid: raw.replace('%ROOT%', 'D:\\Apps'))
        self.assertEqual(app.registered_path('"%ROOT%\\Other.exe"', target), 'D:\\Apps\\Other.exe')
        self.assertEqual(app.registered_path('D:\\App With Spaces\\Other.exe', target), 'D:\\App With Spaces\\Other.exe')
        for raw in ('Other.exe', 'D:\\app.exe --flag', '"D:\\app.exe" --flag', '\\\\remote\\app.exe',
                    '%UNKNOWN%\\app.exe', 'D:\\app.exe\0', None):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                app.registered_path(raw, target)

    def test_reader_binds_translation_source_digest_and_registry_without_use_claim(self):
        resource = version([('040904b0', [('ProductName', 'Unrelated Product'), ('ProductVersion', '3.2')]),
                            ('041104b0', [('ProductName', '翻訳'), ('ProductVersion', '3.2')])])
        data = pe(resource)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'misleading-name.exe'
            path.write_bytes(data)
            target = SimpleNamespace(fs=SimpleNamespace(path=lambda source: path))
            registration = {'hive_path': 'SOFTWARE', 'registry_key': 'App Paths\\anything.exe',
                            'registry_value': '(Default)', 'registered_path': 'D:\\Apps\\anything.exe'}
            ev = Evidence()
            with patch.object(app, '_registered', return_value=[('D:\\Apps\\anything.exe', registration)]):
                app.extract(ev, target, {'common': {'image': 'synthetic.E01', 'exhibit': 'OTHER'}, 'examined_at': 7})
            self.assertEqual(ev.problems, [])
            rows = ev.rows()
            self.assertEqual(len(rows), 13)
            self.assertTrue(all(row[1] == 7 for row in rows))
            self.assertTrue(all(json.loads(row[5])['timestamp_semantics'] == 'examination_observation'
                                for row in rows))
            subjects = [row for row in rows if row[0] == 'attributeSubject']
            self.assertEqual(len({row[4] for row in subjects}), 2)
            literal_values = [decode_value(row[4], 'string') for row in rows if row[0] == 'attributeTextValue']
            self.assertIn('Unrelated Product', literal_values)
            self.assertNotIn('misleading-name', literal_values)
            for row in subjects:
                provenance = json.loads(row[-1])
                self.assertEqual(provenance['file_sha256'], hashlib.sha256(data).hexdigest())
                self.assertEqual(provenance['registrations'], [registration])
                self.assertEqual(data[provenance['byte_offset']:provenance['byte_offset'] + provenance['byte_length']].hex(),
                                 provenance['raw_value_hex'])
                self.assertIn('no execution', provenance['limitation'])
            self.assertEqual({row[0] for row in rows} & {'programRun', 'programInstalled', 'emailSent'}, set())

    def test_bad_source_or_total_limit_does_not_emit_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bad.exe'
            path.write_bytes(b'x' * 100)
            target = SimpleNamespace(fs=SimpleNamespace(path=lambda source: path))
            for limit in (app.MAX_TOTAL_BYTES, 1):
                ev = Evidence()
                with patch.object(app, '_registered', return_value=[('D:\\bad.exe', {})]), patch.object(app, 'MAX_TOTAL_BYTES', limit):
                    app.extract(ev, target, {'common': {'image': 'synthetic'}, 'examined_at': 1})
                self.assertEqual(ev.rows(), [])
                self.assertEqual(len(ev.problems), 1)


if __name__ == '__main__':
    unittest.main()
