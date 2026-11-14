"""Versioned DestList parsing and CFB empty chains, without benchmark data."""
from __future__ import annotations

import io
import json
import struct
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from extractor import windows
from extractor.store import Evidence, FILETIME_EPOCH_100NS

END = 0xFFFFFFFE
FREE = 0xFFFFFFFF
STAMP = FILETIME_EPOCH_100NS + 1_234_567_890


def destlist(version, entries, count=None):
    data = bytearray(32)
    struct.pack_into('<II', data, 0, version, len(entries) if count is None else count)
    offset = 112 if version == 1 else 128
    for number, path, timestamp, properties in entries:
        encoded = path.encode('utf-16-le')
        entry = bytearray(offset + 2)
        struct.pack_into('<II', entry, 88, number, 987)  # adjacent unknown field is not part of ID
        struct.pack_into('<Q', entry, 100, timestamp)
        struct.pack_into('<H', entry, offset, len(encoded) // 2)
        data.extend(entry + encoded)
        if version > 1:
            data.extend(struct.pack('<I', len(properties)) + properties)
    return bytes(data)


def directory(name, kind, start, size, child=FREE):
    row = bytearray(128)
    encoded = (name + '\0').encode('utf-16-le')
    row[:len(encoded)] = encoded
    struct.pack_into('<HBBIII', row, 64, len(encoded), kind, 1, FREE, FREE, child)
    struct.pack_into('<IQ', row, 116, start, size)
    return row


def no_minifat_cfb(empty_destlist=False, payload=None):
    """Valid version-3 CFB: header, FAT, directory, optional >=4096-byte stream."""
    header = bytearray(512)
    header[:8] = bytes.fromhex('d0cf11e0a1b11ae1')
    struct.pack_into('<HHHHH', header, 24, 0x3E, 3, 0xFFFE, 9, 6)
    struct.pack_into('<III', header, 40, 0, 1, 1)
    struct.pack_into('<IIIII', header, 56, 4096, END, 0, END, 0)
    struct.pack_into('<109I', header, 76, 0, *([FREE] * 108))
    sectors = 0 if payload is None else (len(payload) + 511) // 512
    if payload is not None and len(payload) < 4096:
        raise ValueError('helper uses ordinary FAT streams only')
    fat = [0xFFFFFFFD, END] + [FREE] * 126
    for i in range(sectors):
        fat[i + 2] = i + 3 if i + 1 < sectors else END
    has_child = empty_destlist or payload is not None
    rows = directory('Root Entry', 5, END, 0, 1 if has_child else FREE)
    if has_child:
        rows += directory('DestList', 2, END if payload is None else 2,
                          0 if payload is None else len(payload))
    rows += bytes(512 - len(rows))
    body = b'' if payload is None else payload + bytes(sectors * 512 - len(payload))
    return bytes(header) + struct.pack('<128I', *fat) + rows + body


class CompoundFiles(unittest.TestCase):
    def test_absent_minifat_and_empty_streams_are_valid(self):
        for has_destlist in (False, True):
            with self.subTest(has_destlist=has_destlist):
                raw = no_minifat_cfb(has_destlist)
                ole = windows._JumpListOLE(io.BytesIO(raw))
                self.assertEqual(ole.root.open().read(), b'')
                self.assertEqual(list(ole.root.listdir()), ['DestList'] if has_destlist else [])
                if has_destlist:
                    self.assertEqual(windows._jumplist_stream(ole, 'DestList'), b'')
                    self.assertEqual(windows._destlist(windows._jumplist_stream(ole, 'DestList')), {})

    def test_absent_minifat_can_still_have_large_ordinary_streams(self):
        payload = bytes(range(256)) * 16
        ole = windows._JumpListOLE(io.BytesIO(no_minifat_cfb(payload=payload)))
        self.assertEqual(windows._jumplist_stream(ole, 'DestList'), payload)

    def test_nonempty_minifat_or_stream_cannot_start_at_endofchain(self):
        raw = bytearray(no_minifat_cfb())
        struct.pack_into('<I', raw, 64, 1)
        with self.assertRaisesRegex(ValueError, 'nonempty chain'):
            windows._JumpListOLE(io.BytesIO(raw))
        raw = bytearray(no_minifat_cfb(True))
        struct.pack_into('<Q', raw, 1024 + 128 + 120, 10)
        with self.assertRaisesRegex(ValueError, 'nonempty mini stream'):
            windows._JumpListOLE(io.BytesIO(raw)).root.listdir()

    def test_corrupt_directory_chain_is_not_hidden(self):
        raw = bytearray(no_minifat_cfb())
        struct.pack_into('<I', raw, 48, END)
        with self.assertRaisesRegex(ValueError, 'directory chain is absent'):
            windows._JumpListOLE(io.BytesIO(raw))

    def test_stream_size_limit_prevents_reading(self):
        entry = SimpleNamespace(size=16 * 1024 * 1024 + 1,
                                open=lambda: self.fail('oversized stream was read'))
        with self.assertRaisesRegex(ValueError, 'parsing limit'):
            windows._jumplist_stream(SimpleNamespace(get=lambda name: entry), 'large')


class DestLists(unittest.TestCase):
    def test_versions_one_through_four_keep_original_path_and_record_id(self):
        rows = [(0x1A, 'D:\\Different\\résumé😀.txt', STAMP, b''),
                (9, 'E:\\Folder\\other.bin', STAMP + 123, b'')]
        expected = {'1a': (STAMP, rows[0][1]), '9': (STAMP + 123, rows[1][1])}
        for version in (1, 2, 3, 4):
            with self.subTest(version=version):
                self.assertEqual(windows._destlist(destlist(version, rows)), expected)

    def test_property_store_size_controls_next_record_boundary(self):
        rows = [(1, r'D:\One', STAMP, b'not merely four bytes of padding'),
                (2, r'D:\Two', STAMP + 99, b'')]
        self.assertEqual(windows._destlist(destlist(4, rows)),
                         {'1': (STAMP, r'D:\One'), '2': (STAMP + 99, r'D:\Two')})

    def test_empty_stream_is_valid_but_unsupported_or_truncated_header_is_not(self):
        self.assertEqual(windows._destlist(b''), {})
        for raw in (b'\0', bytes(31), destlist(99, [])):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                windows._destlist(raw)

    def test_truncation_and_declared_count_mismatch_fail_instead_of_guessing(self):
        raw = destlist(4, [(1, r'D:\One', STAMP, b'properties')])
        for broken in (raw[:90], raw[:-12], raw[:-1],
                       destlist(4, [], count=1), destlist(4, [(1, r'D:\One', STAMP, b'')], count=0)):
            with self.subTest(length=len(broken)), self.assertRaises(ValueError):
                windows._destlist(broken)

    def test_duplicate_ids_and_invalid_unicode_are_not_replaced_or_overwritten(self):
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            windows._destlist(destlist(1, [(1, r'D:\One', STAMP, b''), (1, r'D:\Two', STAMP, b'')]))
        raw = bytearray(destlist(1, [(1, 'A', STAMP, b'')]))
        raw[-2:] = b'\x00\xd8'
        with self.assertRaises(UnicodeDecodeError):
            windows._destlist(raw)

    def test_reader_emits_only_filesystem_targets_and_preserves_timestamp_semantics(self):
        from tests.test_inventory import FS
        fs = FS()
        name = 'C:/Users/Someone/AppData/Roaming/Microsoft/Windows/Recent/AutomaticDestinations/example.automaticDestinations-ms'
        fs.add(name)
        raw = destlist(4, [(1, r'D:\Files\different.txt', STAMP, b''),
                           (2, 'ms-settings:network', STAMP + 100, b'')])
        lnk = bytearray(80)
        struct.pack_into('<I', lnk, 0, 76)
        lnk[4:20] = bytes.fromhex('0114020000000000c000000000000046')
        struct.pack_into('<I', lnk, 60, 1)
        streams = {'DestList': raw, '1': bytes(lnk), '2': bytes(lnk)}
        ole = SimpleNamespace(root=SimpleNamespace(listdir=lambda: streams),
                              get=lambda key: SimpleNamespace(size=len(streams[key]), open=lambda: io.BytesIO(streams[key])))
        ev = Evidence()
        with patch.object(windows, '_JumpListOLE', return_value=ole):
            count = windows._jumplists(ev, SimpleNamespace(fs=fs), {'image': 'imaginary.E01', 'exhibit': 'Device', 'tool': 'test'})
        self.assertEqual(count, 1)
        kind, time, resolution, obj, aux, raw_prov = ev.rows()[0]
        prov = json.loads(raw_prov)
        self.assertEqual((kind, time, obj, aux), ('lnkTarget', 123456789, r'\Files\different.txt', ''))
        self.assertEqual(prov['destlist_version'], 4)
        self.assertEqual(prov['timestamp_semantics'], 'destlist_entry_update')
        self.assertEqual(prov['destlist_filetime'], STAMP)
        self.assertIn('not target-file modification', prov['time_meaning'])
        self.assertEqual(len(ev.problems), 1)
        self.assertIn('ms-settings:network', ev.problems[0])


if __name__ == '__main__':
    unittest.main()
