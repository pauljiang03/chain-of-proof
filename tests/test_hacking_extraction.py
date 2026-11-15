"""Synthetic legacy artifacts; never load case images or a benchmark answer key."""
import io
import json
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from extractor import hacking
from extractor.store import Evidence
from scripts import fetch_hacking_case as download


def packet(payload, seq=100, ports=(1234, 80), flags=0x18):
    tcp = struct.pack('>HHIIBBHHH', *ports, seq, 0, 5 << 4, flags, 0, 0, 0) + payload
    ip = struct.pack('>BBHHHBBH4s4s', 0x45, 0, 20 + len(tcp), 0, 0, 64, 6, 0,
                     b'\xc0\x00\x02\x01', b'\xc6\x33\x64\x01') + tcp
    return b'\0' * 12 + b'\x08\x00' + ip


def pcap(*packets):
    result = b'\xd4\xc3\xb2\xa1' + struct.pack('<HHIIII', 2, 4, 0, 0, 65535, 1)
    for frame in packets:
        result += struct.pack('<4I', 1700000000, 123456, len(frame), len(frame)) + frame
    return result


def info2(path=r'D:\Example\tool.exe', *, version=5, size=800):
    row = bytearray(size)
    raw = path.encode('cp1252')
    row[:len(raw)] = raw
    struct.pack_into('<IIQI', row, 260, 7, 3, 133444736000000000, 9)
    if size == 800:
        encoded = path.encode('utf-16-le')
        row[280:280 + len(encoded)] = encoded
    return struct.pack('<5I', version, 1, 1, size, 9) + row


def ie_index(location='Visited:Other@https://example.test/page', *, allocated=True, version='5.2'):
    data = bytearray(0x4200)
    signature = ('Client UrlCache MMF Ver ' + version).encode()
    data[:len(signature)] = signature
    data[0x250] = 15 if allocated else 0
    data[0x4000:0x4004] = b'URL '
    struct.pack_into('<IQQ', data, 0x4004, 4, 0, 133444736000000000)
    field = 52 if version == '5.2' else 56
    struct.pack_into('<I', data, 0x4000 + field, 104)
    value = location.encode() + b'\0'
    data[0x4068:0x4068 + len(value)] = value
    return data


def dbx(source_type=0):
    data = bytearray(0x24bc + 0x618)
    magic = bytes.fromhex('cfad12fec5fd746f66e3d1119a4e00c04fa309d4')
    data[:len(magic)] = magic
    struct.pack_into('<I', data, 0x1c, 0x618)
    struct.pack_into('<I', data, 0x24bc, 1)
    data[0x24c0] = source_type
    data[0x24c1:0x24c1 + 9] = b'account-9'
    name = b'example.newsgroup'
    data[0x25c1:0x25c1 + len(name)] = name
    return data


class LegacyParsers(unittest.TestCase):
    def test_ini_keeps_exact_lines_duplicates_and_no_interpolation(self):
        data = b'; literal\r\n[Profile]\r\nFullName="Someone Else"\r\nEMailAddress=a@example.test\r\nEMailAddress=b@example.test\r\n'
        rows = list(hacking.config_attributes(data))
        self.assertEqual([row[:2] for row in rows], [('app.config.real_name', 'Someone Else'),
                          ('app.config.email', 'a@example.test'), ('app.config.email', 'b@example.test')])
        for _, _, row in rows:
            raw = data[row['byte_offset']:row['byte_offset'] + row['byte_length']]
            self.assertEqual(raw.decode('cp1252').rstrip('\r\n'), row['raw_line'])
        self.assertEqual(rows[0][2]['line'], 3)

    def test_typed_false_is_not_missing_and_mirc_defaults_are_not_channel_access(self):
        data = b'[Variables]\n%ISUSERNTADMIN%=FALSE\n%LANUSER%=DifferentUser\n[chanfolder]\nn0=#default\n'
        rows = list(hacking.config_attributes(data))
        self.assertIs(rows[0][1], False)
        self.assertEqual(rows[1][1], 'DifferentUser')
        self.assertEqual(list(hacking.irc_channels(data)), [])
        logs = list(hacking.irc_channels(b'Session Ident: #real-channel\r\nSession Ident: privateNick\r\n'))
        self.assertEqual([row[0] for row in logs], ['#real-channel'])

    def test_utf16_ini_offsets_and_invalid_admin_are_explicit(self):
        data = b'\xff\xfe' + '[mirc]\r\nuser=Another Name\r\n'.encode('utf-16-le')
        role, value, row = next(hacking.config_attributes(data))
        self.assertEqual((role, value), ('app.config.real_name', 'Another Name'))
        self.assertEqual(data[row['byte_offset']:row['byte_offset'] + row['byte_length']].decode('utf-16-le'),
                         'user=Another Name\r\n')
        with self.assertRaises(ValueError):
            list(hacking.config_attributes(b'[Variables]\n%ISUSERNTADMIN%=perhaps\n'))

    def test_mac_normalization_retains_literal_source(self):
        for raw in ('aabbccddeeff', 'aa-bb-cc-dd-ee-ff', 'aa:bb:cc:dd:ee:ff', 'aabb.ccdd.eeff'):
            role, value, locator = next(hacking.config_attributes(f'[Variables]\n%LANNIC%={raw}\n'.encode()))
            self.assertEqual((role, value), ('network.mac_address', 'AA:BB:CC:DD:EE:FF'))
            self.assertEqual(locator['original_value'], raw)
        with self.assertRaisesRegex(ValueError, 'MAC'):
            list(hacking.config_attributes(b'[Variables]\n%LANNIC%=not-an-address\n'))

    def test_channel_log_filename_requires_actual_channel_header(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'mIRC' / 'logs'
            root.mkdir(parents=True)
            good, bad = root / '#example.Network.log', root / 'private.Network.log'
            good.write_bytes(b'Session Ident: #example\r\n')
            bad.write_bytes(b'Session Ident: private\r\n')
            ev = Evidence()
            hacking._logs(ev, [good, bad], {'common': {'image': 'synthetic', 'exhibit': 'FIX'}, 'examined_at': 1})
            rows = [json.loads(row[-1]) for row in ev.rows() if row[0] == 'attributeSubject']
            logs = [row for row in rows if row['attribute_role'] == 'app.config.irc_log_file_name']
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0]['channel_from_session_ident'], '#example')
            self.assertTrue(logs[0]['source_path'].endswith('#example.Network.log'))

    def test_dbx_typed_original_mailbox_name_does_not_assert_subscription(self):
        row = hacking.dbx_mailbox(dbx())
        self.assertEqual(row['name'], 'example.newsgroup')
        self.assertEqual(row['account_key'], 'account-9')
        self.assertIn('does not establish current subscription', row['note'])
        self.assertIsNone(hacking.dbx_mailbox(dbx(3)))
        for value in (dbx()[:-1], b'name-only.dbx', dbx(9)):
            with self.assertRaises(ValueError):
                hacking.dbx_mailbox(value)

    def test_ie_index_offsets_allocation_and_string_bounds(self):
        for version in ('4.7', '5.2'):
            row, = hacking.msie_url_records(ie_index(version=version))
            self.assertEqual(row['location'], 'Visited:Other@https://example.test/page')
            self.assertEqual(row['primary_filetime'], 133444736000000000)
            self.assertEqual(row['location_locator']['byte_offset'], 0x4068)
        self.assertEqual(list(hacking.msie_url_records(ie_index(allocated=False))), [])
        invalid = ie_index()
        struct.pack_into('<I', invalid, 0x4000 + 52, 513)
        with self.assertRaisesRegex(ValueError, 'string pointer'):
            list(hacking.msie_url_records(invalid))
        invalid = ie_index()
        invalid[0x250] = 1
        with self.assertRaisesRegex(ValueError, 'unallocated'):
            list(hacking.msie_url_records(invalid))

    def test_only_global_history_creates_visit_not_cache_or_weekly_record(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = []
            for location in ('History/History.IE5', 'History/History.IE5/MSHist012023010120230108',
                             'Temporary Internet Files/Content.IE5'):
                path = root / location / 'index.dat'
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(ie_index())
                files.append(path)
            ev = Evidence()
            hacking._browser_indexes(ev, files, {'common': {'image': 'synthetic', 'exhibit': 'FIX'}, 'examined_at': 5})
            visits = [row for row in ev.rows() if row[0] == 'webVisit']
            self.assertEqual(len(visits), 1)
            self.assertEqual(visits[0][1], 1700000000000000)
            self.assertEqual(visits[0][3], 'https://example.test/page')
            self.assertEqual(len([row for row in ev.rows() if row[0] == 'attributeSubject'
                                  and json.loads(row[-1])['attribute_role'] == 'browser.url']), 3)

    def test_info2_uses_recorded_path_drive_timestamp_and_bounds(self):
        row, = hacking.info2_records(info2())
        self.assertEqual(row['original_path'], r'D:\Example\tool.exe')
        self.assertEqual(row['drive'], 'D')
        self.assertEqual(row['record_index'], 7)
        self.assertEqual(row['byte_offset'], 20)
        self.assertEqual(row['deleted_us'], 1700000000000000)
        for invalid in (b'', info2()[:-1], info2(version=9), info2(path='relative.exe')):
            with self.subTest(invalid=invalid[:20]), self.assertRaises(ValueError):
                list(hacking.info2_records(invalid))

    def test_pcap_contiguous_reassembly_and_exact_payload_offsets(self):
        first = b'GET /different HTTP/1.1\r\nHost: exa'
        second = b'mple.test\r\nUser-Agent: Test-device\r\n\r\n'
        data = pcap(packet(first), packet(second, 100 + len(first)))
        row, = hacking.http_requests(data)
        self.assertEqual(row['headers']['host'], ['example.test'])
        self.assertEqual(row['headers']['user-agent'], ['Test-device'])
        self.assertEqual(row['request_target'], '/different')
        for location, expected in zip(row['packets'], (first, second)):
            self.assertEqual(data[location['byte_offset']:location['byte_offset'] + location['byte_length']], expected)
        self.assertEqual(row['packets'][0]['packet_time_us'], 1700000000123456)

    def test_gaps_conflicts_responses_and_body_text_do_not_invent_requests(self):
        first = b'GET / HTTP/1.1\r\nHost: exa'
        second = b'mple.test\r\n\r\n'
        self.assertEqual(list(hacking.http_requests(pcap(packet(first), packet(second, 101 + len(first))))), [])
        with self.assertRaisesRegex(ValueError, 'conflicting TCP'):
            list(hacking.http_requests(pcap(packet(first), packet(b'X' + first[1:]))))
        body = b'GET /fake HTTP/1.1\r\nHost: fake.test\r\n\r\n'
        response = b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\n' + body
        self.assertEqual(list(hacking.http_requests(pcap(packet(response, ports=(80, 1234))))), [])
        posted = b'POST /real HTTP/1.1\r\nHost: example.test\r\nContent-Length: ' + str(len(body)).encode() + b'\r\n\r\n' + body
        rows = list(hacking.http_requests(pcap(packet(posted))))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['request_target'], '/real')
        with self.assertRaisesRegex(ValueError, 'truncated'):
            list(hacking.http_requests(pcap(packet(first))[:-1]))

    def test_sid_named_user_hive_is_read_and_missing_values_not_invented(self):
        values = [SimpleNamespace(name='SMTP Email Address', value='new@example.test'),
                  SimpleNamespace(name='NNTP Server', value=''), SimpleNamespace(name='SMTP Password', value='excluded')]
        account = SimpleNamespace(path='Software\\Microsoft\\Internet Account Manager\\Accounts\\1', values=lambda: values)
        hive = SimpleNamespace(name='S-1-5-21-NEW', path='sysvol\\Profiles\\Other\\NTUSER.DAT',
                               account='Other', sid='S-1-5-21-NEW', hive=SimpleNamespace(key=lambda path: SimpleNamespace(subkeys=lambda: [account])))
        target = SimpleNamespace(registry=SimpleNamespace(load_user_hives=lambda: None))
        ev = Evidence()
        with patch('extractor.system._hives', return_value=[hive]):
            hacking._mail_accounts(ev, target, {'common': {'image': 'other.E01', 'exhibit': 'OTHER'}, 'examined_at': 1})
        attributes = [json.loads(row[-1]) for row in ev.rows() if row[0] == 'attributeSubject']
        self.assertEqual([row['attribute_role'] for row in attributes], ['app.config.email'])
        self.assertEqual(attributes[0]['registry_value'], 'SMTP Email Address')
        self.assertTrue(all(row[1] == 1 for row in ev.rows()))

    def test_attribute_subject_is_bound_to_image_and_exact_source(self):
        ev = Evidence()
        for image in ('a.E01', 'b.E01'):
            hacking._emit(ev, {'common': {'image': image, 'exhibit': 'PC'}, 'examined_at': 2},
                          r'C:\config.ini', 'app.config.email', 'same@example.test', byte_offset=8)
        subjects = [row for row in ev.rows() if row[0] == 'attributeSubject']
        self.assertEqual(len(subjects), 2)
        self.assertNotEqual(subjects[0][3], subjects[1][3])


class DownloadTests(unittest.TestCase):
    def test_download_only_official_allowlisted_files_and_preserve_existing(self):
        self.assertEqual(len(download.FILES), 3)
        self.assertTrue(all('Answers' not in url and url.startswith('https://cfreds-archive.nist.gov/images/')
                            for _, url in download.FILES))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'fixture').write_bytes(b'evidence')
            with patch.object(download, 'urlopen', side_effect=AssertionError('must not redownload')):
                record = download.fetch(root, 'fixture', 'https://example.test/fixture')
            self.assertEqual(record['status'], 'existing_file_not_redownloaded')
            self.assertEqual(record['bytes'], 8)

    def test_unbound_partial_is_restarted_and_truncation_is_never_published(self):
        class Response(io.BytesIO):
            status = 200
            headers = {'Content-Length': '3', 'ETag': '"new"'}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'fixture.part').write_bytes(b'old bytes')
            with patch.object(download, 'urlopen', return_value=Response(b'new')) as opener:
                download.fetch(root, 'fixture', 'https://example.test/fixture')
            self.assertNotIn('Range', opener.call_args[0][0].headers)
            self.assertEqual((root / 'fixture').read_bytes(), b'new')
            with patch.object(download, 'urlopen', return_value=Response(b'x')), self.assertRaises(ValueError):
                download.fetch(root, 'truncated', 'https://example.test/truncated')
            self.assertFalse((root / 'truncated').exists())

    def test_resume_requires_same_object_and_complete_remaining_range(self):
        class Response(io.BytesIO):
            status = 206
            def __init__(self, headers, body=b'new'):
                super().__init__(body)
                self.headers = headers
        url = 'https://example.test/fixture'
        cases = [({'Content-Range': 'bytes 3-5/6', 'ETag': '"same"'}, True),
                 ({'Content-Range': 'bytes 3-5/9', 'ETag': '"same"'}, False),
                 ({'Content-Range': 'bytes 3-5/6', 'ETag': '"changed"'}, False),
                 ({'Content-Range': 'bytes 3-6/7', 'ETag': '"same"'}, False)]
        for headers, valid in cases:
            with self.subTest(headers=headers), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / 'fixture.part').write_bytes(b'old')
                (root / 'fixture.part.json').write_text(json.dumps({'url': url, 'etag': '"same"'}))
                with patch.object(download, 'urlopen', return_value=Response(headers)):
                    if valid:
                        download.fetch(root, 'fixture', url)
                        self.assertEqual((root / 'fixture').read_bytes(), b'oldnew')
                    else:
                        with self.assertRaises(ValueError):
                            download.fetch(root, 'fixture', url)
                        self.assertFalse((root / 'fixture').exists())


if __name__ == '__main__':
    unittest.main()
