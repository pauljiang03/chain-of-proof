"""Filesystem names use the real Dissect wchar parser type, not a str mock."""
import io
import json
from pathlib import PureWindowsPath
from types import SimpleNamespace
import unittest

try:
    from dissect.cstruct import cstruct
except ImportError:
    cstruct = None

from extractor import hacking
from extractor.attributes import emit_attribute
from extractor.store import Evidence
from tests.test_hacking_extraction import packet, pcap


class NativePath:
    def __init__(self, source, data):
        self.source, self.data = source, data
        parser = cstruct().load('struct NativeName { uint8 length; wchar name[length]; };')
        literal = PureWindowsPath(source).name.encode('utf-16-le')
        self.name = parser.NativeName(bytes([len(literal) // 2]) + literal).name
        self.suffix = PureWindowsPath(source).suffix

    def __str__(self):
        return self.source

    def stat(self):
        return SimpleNamespace(st_size=len(self.data))

    def open(self, mode):
        assert mode == 'rb'
        return io.BytesIO(self.data)


@unittest.skipUnless(cstruct, 'optional Dissect parser is not installed')
class NativeFilesystemNames(unittest.TestCase):
    def setUp(self):
        self.ctx = {'common': {'image': 'synthetic.E01', 'exhibit': 'FIX',
                    'source_snapshot': 'base-volume', 'source_variant': 'primary'}, 'examined_at': 123}

    def values(self, ev, role):
        return [json.loads(row[4]) for row in ev.rows() if row[0] == 'attributeTextValue'
                and json.loads(row[-1])['attribute_role'] == role]

    def test_real_wchar_filename_remains_exact_and_cache_scan_continues(self):
        for name in ('MiXeD café[1].htm', 'index.dat'):
            path = NativePath('C:\\Users\\Other\\Local Settings\\Temporary Internet Files\\' + name,
                              b'Literal retained text fixture@example.invalid')
            self.assertIsInstance(path.name, str)
            self.assertIsNot(type(path.name), str)
            # The shared emitter must remain strict; only this reader adapts its
            # validated filesystem-text input before crossing that boundary.
            with self.assertRaises(ValueError):
                emit_attribute(Evidence(), 'fixture', 'browser.cache_file_name', path.name, 123)
            ev = Evidence()
            hacking._browser(ev, [path], self.ctx)
            self.assertFalse(ev.problems)
            self.assertEqual(self.values(ev, 'browser.cache_file_name'), [name])
            self.assertEqual(self.values(ev, 'browser.email_address'), ['fixture@example.invalid'])
            self.assertEqual(self.values(ev, 'source.path'), [path.source])

    def test_irc_and_capture_names_use_the_same_literal_adapter(self):
        log = NativePath('C:\\Tools\\mIRC\\logs\\#MiXeD café.Network.log', b'Session Ident: #MiXeD\r\n')
        capture = NativePath('C:\\Captures\\MiXeD café.pcap',
                             pcap(packet(b'GET /fixture HTTP/1.1\r\nHost: example.invalid\r\n\r\n')))
        for path, reader, role in ((log, hacking._logs, 'app.config.irc_log_file_name'),
                                   (capture, hacking._traffic, 'traffic.file_name')):
            ev = Evidence()
            reader(ev, [path], self.ctx)
            self.assertFalse(ev.problems)
            self.assertEqual(self.values(ev, role), [str.__str__(path.name)])
        self.assertEqual(self.values(ev, 'traffic.url'), ['http://example.invalid/fixture'])

    def test_nontext_names_are_not_stringified_and_string_contents_are_not_rewritten(self):
        for value in (b'bytes.htm', 42, False, None, object()):
            with self.subTest(value=value), self.assertRaises(ValueError):
                hacking._file_name(SimpleNamespace(name=value))
        class MisleadingString(str):
            def __str__(self):
                return 'rewritten'
        value = MisleadingString('Literal MiXeD é.txt')
        self.assertEqual(hacking._file_name(SimpleNamespace(name=value)), 'Literal MiXeD é.txt')
        self.assertIs(type(hacking._file_name(SimpleNamespace(name=value))), str)


if __name__ == '__main__':
    unittest.main()
