"""Literal note content is paired with its container's own filesystem time."""
import json
import struct
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from extractor import artifact_containers as ac
from extractor.store import Evidence
from tests.test_artifact_containers import STICKY, sqlite_bytes
from tests.test_inventory import FS, Path as FixturePath


NOTE_ID = '12345678-1234-1234-123456789012'
MODIFIED_NS = 1700000000123456700
OLE_STORAGE_TIME = 133000000000000000
SOURCE = 'C:/Users/Example/AppData/Local/Packages/Microsoft.MicrosoftStickyNotes_example/LocalState/plum.sqlite'
SNT_SOURCE = 'C:/Users/Example/AppData/Roaming/Microsoft/Sticky Notes/StickyNotes.snt'
ORIGIN = dict(image='synthetic.E01', exhibit='EXAMPLE', source_snapshot='base-volume', source_variant='primary')


def snt_bytes(text='Literal Unicode Ω\r\n', *, stream_bytes=None, duplicate_stream=False, nested_text=False):
    """Small standard-sector OLE fixture with real MiniFAT text streams."""
    free, end = 0xffffffff, 0xfffffffe
    data = bytearray(512 * 6)
    data[:8] = bytes.fromhex('d0cf11e0a1b11ae1')
    struct.pack_into('<5H', data, 24, 0x3e, 3, 0xfffe, 9, 6)
    struct.pack_into('<9I', data, 40, 0, 1, 1, 0, 4096, 4, 1, end, 0)
    struct.pack_into('<109I', data, 76, 0, *([free] * 108))
    struct.pack_into('<128I', data, 512, 0xfffffffd, 2, end, end, end, *([free] * 123))
    raw = (text + '\0').encode('utf-16-le') if stream_bytes is None else stream_bytes
    streams = [b'1', b'meta', b'{\\rtf1 fixture}', raw]
    if any(len(stream) > 64 for stream in streams):
        raise ValueError('fixture supports one mini sector per stream')
    for index, stream in enumerate(streams):
        data[2048 + index * 64:2048 + index * 64 + len(stream)] = stream
    struct.pack_into('<128I', data, 2560, end, end, end, end, *([free] * 124))

    def entry(sid, name, kind, *, right=free, child=free, start=0, size=0, modified=0):
        offset = 1024 + sid * 128
        encoded = (name + '\0').encode('utf-16-le')
        data[offset:offset + len(encoded)] = encoded
        struct.pack_into('<HBBIII', data, offset + 64, len(encoded), kind, 1, free, right, child)
        struct.pack_into('<QQIQ', data, offset + 100, 0, modified, start, size)

    entry(0, 'Root Entry', 5, child=1, start=3, size=256)
    entry(1, 'Version', 2, right=2, size=len(streams[0]))
    entry(2, 'Metafile', 2, right=3, start=1, size=len(streams[1]))
    entry(3, NOTE_ID, 1, child=4, modified=OLE_STORAGE_TIME)
    entry(4, '0', 2, right=5, start=2, size=len(streams[2]))
    entry(5, '0' if duplicate_stream else '3', 2, start=3, size=len(raw))
    if nested_text:
        entry(5, 'nested', 1, child=6)
        entry(6, '3', 2, start=3, size=len(raw))
    return bytes(data)


def source_rows(ev):
    return [dict(kind=kind, time=time, obj=obj, aux=aux, prov=json.loads(prov))
            for kind, time, res, obj, aux, prov in ev.rows()]


class StickyNotes(unittest.TestCase):
    def extract(self, data, *, path=SOURCE, modified_ns=MODIFIED_NS, common=None):
        fs = FS()
        fs.add(path, data=data)
        target = NS(fs=fs, user_details=NS(all_with_home=lambda: []))
        ctx = dict(common=common or ORIGIN, examined_at=1800000000000000)
        ev = Evidence()
        original_stat = FixturePath.lstat
        def stat(item):
            result = original_stat(item)
            if modified_ns is not None:
                result.st_mtime_ns = modified_ns
            return result
        with patch.object(FixturePath, 'lstat', stat):
            ac.extract(ev, target, ctx)
        return source_rows(ev), ev

    def values(self, rows):
        return [row for row in rows if row['kind'] == 'attributeTextValue']

    def test_sqlite_literal_content_path_and_container_time_share_note_subject(self):
        raw = sqlite_bytes(STICKY + "INSERT INTO Note VALUES ('note-a', 'line 1'||char(10)||'Ω line 2', 1, 2);")
        rows, ev = self.extract(raw)
        self.assertFalse(ev.problems)
        values = self.values(rows)
        text = [row for row in values if row['prov']['attribute_role'] == 'sticky_notes.note.text']
        self.assertEqual(len(text), 1)
        self.assertEqual(json.loads(text[0]['aux']), 'line 1\nΩ line 2')
        note = [row for row in values if 'note_locator' in row['prov']]
        self.assertEqual(len(note), 3)
        subjects = {row['aux'] for row in rows if row['kind'] == 'attributeSubject' and 'note_locator' in row['prov']}
        self.assertEqual(len(subjects), 1)
        fields = {row['prov']['attribute_role']: json.loads(row['aux']) for row in note}
        self.assertEqual(fields['sticky_notes.container.path'], SOURCE.replace('/', '\\'))
        self.assertEqual(fields['sticky_notes.container.modified_at'], '2023-11-14T22:13:20.1234567Z')
        for row in rows:
            self.assertEqual(row['time'], 1800000000000000)
        modified = next(row for row in note if row['prov']['attribute_role'] == 'sticky_notes.container.modified_at')
        self.assertEqual(modified['prov']['source_field'], 'filesystem lstat.st_mtime_ns')
        self.assertEqual(modified['prov']['filesystem_mtime_ns'], MODIFIED_NS)
        self.assertEqual(text[0]['prov']['note_locator'], {'table': 'Note', 'rowid': 1, 'id': 'note-a'})
        self.assertIn('WAL not replayed', text[0]['prov']['wal_policy'])

    def test_real_ole_parser_reads_unicode_stream_not_rtf_or_storage_time(self):
        try:
            import dissect.ole
        except ImportError:
            self.skipTest('optional OLE parser unavailable')
        rows, ev = self.extract(snt_bytes(), path=SNT_SOURCE)
        self.assertFalse(ev.problems, ev.problems)
        fields = {row['prov']['attribute_role']: json.loads(row['aux']) for row in self.values(rows)}
        self.assertEqual(fields['sticky_notes.note.text'], 'Literal Unicode Ω\r\n')
        self.assertEqual(fields['sticky_notes.container.modified_at'], '2023-11-14T22:13:20.1234567Z')
        text = next(row for row in self.values(rows) if row['prov']['attribute_role'] == 'sticky_notes.note.text')
        self.assertEqual(text['prov']['note_locator'], {'storage': NOTE_ID, 'storage_sid': 3, 'stream': '3', 'stream_sid': 5})

    def test_duplicate_ids_null_blob_or_invalid_unicode_do_not_emit_partial_note_rows(self):
        for inserts in ("('a', 'one', 1, 2), ('a', 'two', 1, 2)",
                        "('a', 'one', 1, 2), ('A', 'two', 1, 2)",
                        "('a', NULL, 1, 2)", "('a', X'626f6479', 1, 2)",
                        "('', 'body', 1, 2)", "('a', CAST(X'FF' AS TEXT), 1, 2)"):
            with self.subTest(inserts=inserts):
                rows, ev = self.extract(sqlite_bytes(STICKY + 'INSERT INTO Note VALUES ' + inserts + ';'))
                self.assertEqual(rows, [])
                self.assertTrue(ev.problems)

    def test_empty_text_is_preserved_not_confused_with_missing_value(self):
        rows, ev = self.extract(sqlite_bytes(STICKY + "INSERT INTO Note VALUES ('empty', '', 0, 0);"))
        text, = [json.loads(row['aux']) for row in self.values(rows) if row['prov']['attribute_role'] == 'sticky_notes.note.text']
        self.assertEqual(text, '')
        self.assertFalse(ev.problems)

    def test_missing_or_bad_filesystem_time_never_uses_note_updated_at(self):
        raw = sqlite_bytes(STICKY + "INSERT INTO Note VALUES ('a', 'body', 1234, 999999999);")
        for stamp in (None, True, '2026', 1.5, 10**40):
            with self.subTest(stamp=stamp):
                rows, ev = self.extract(raw, modified_ns=stamp)
                roles = {row['prov']['attribute_role'] for row in self.values(rows)}
                self.assertEqual(roles, {'sticky_notes.container.path', 'sticky_notes.note.text'})
                self.assertTrue(ev.problems)

    def test_distinct_notes_containers_and_origins_do_not_share_subjects(self):
        raw = sqlite_bytes(STICKY + "INSERT INTO Note VALUES ('a', 'same text', 1, 2), ('b', 'same text', 1, 2);")
        def subjects(rows):
            return {row['aux'] for row in rows if row['kind'] == 'attributeSubject' and 'note_locator' in row['prov']}
        original = subjects(self.extract(raw)[0])
        self.assertEqual(len(original), 2)
        for options in (dict(path=SOURCE.replace('Example', 'Other', 1)),
                        dict(common=dict(ORIGIN, image='other.E01')),
                        dict(common=dict(ORIGIN, source_variant='recovered')),
                        dict(common=dict(ORIGIN, source_snapshot='vss:aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'))):
            self.assertFalse(original & subjects(self.extract(raw, **options)[0]))

    def test_note_counts_and_aggregate_text_are_bounded_before_emission(self):
        raw = sqlite_bytes(STICKY + "INSERT INTO Note VALUES ('a', '1234', 1, 2), ('b', '5678', 1, 2);")
        for key, limit in (('MAX_RECORDS', 1), ('MAX_TEXT_BYTES', 3), ('MAX_NOTE_TEXT_BYTES', 7)):
            with self.subTest(key=key), patch.object(ac, key, limit):
                rows, ev = self.extract(raw)
                self.assertEqual(rows, [])
                self.assertTrue(ev.problems)

    def test_ole_ambiguous_nested_and_malformed_text_streams_are_rejected(self):
        try:
            import dissect.ole
        except ImportError:
            self.skipTest('optional OLE parser unavailable')
        for data in (snt_bytes(duplicate_stream=True), snt_bytes(nested_text=True),
                     snt_bytes(stream_bytes=b'x'), snt_bytes(stream_bytes=b'\x00\xd8'),
                     snt_bytes(stream_bytes='a\0b'.encode('utf-16-le'))):
            with self.subTest(digest=len(data)):
                rows, ev = self.extract(data, path=SNT_SOURCE)
                self.assertEqual(rows, [])
                self.assertTrue(ev.problems)


if __name__ == '__main__':
    unittest.main()
