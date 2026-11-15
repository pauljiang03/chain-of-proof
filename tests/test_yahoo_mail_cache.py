"""Source-byte fixtures, without case images, benchmark keys or filename patterns."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from checker.catalog import ROLES
from extractor import yahoo_mail_cache as yahoo
from extractor.store import Evidence


URL = 'https://us.f999.mail.yahoo.com/ym/ShowLetter?box=Inbox&MsgId=synthetic-42'


def html(message_id='synthetic-42', body='A synthetic message body.', label='Subject:'):
    return (f'<html><head><title>Yahoo! Mail</title></head><body>'
            f'<form name=showLetter method=post action="/ym/ShowLetter?box=Inbox">'
            f'<input type=hidden name=MsgId value="{message_id}"></form>'
            f'<table><tr><td><b>From:</b></td><td>fixture@example.test</td></tr>'
            f'<tr><td>{label}</td><td>A synthetic subject</td></tr>'
            f'<tr><td>Date:</td><td>Mon, 4 Sep 2023 12:00:00 +0000</td></tr></table>'
            f'<div id=message>{body}</div></body></html>').encode()


def index(data=None, *, url=URL, filename='unrelated-cache-name.htm', directory='ABCD1234',
          version='5.2', directory_index=0, allocated=True, flags=1):
    if data is None:
        data = html()
    result = bytearray(0x4400)
    signature = ('Client UrlCache MMF Ver ' + version).encode()
    result[:len(signature)] = signature
    struct.pack_into('<I', result, 72, 1)
    result[80:88] = directory.encode()
    result[0x250] = 0xff if allocated else 0
    result[0x4000:0x4004] = b'URL '
    struct.pack_into('<I', result, 0x4004, 8)
    struct.pack_into('<Q', result, 0x4020, len(data))
    location_field, directory_field, filename_field, flags_field = ((56, 60, 64, 68)
                                                                  if version == '4.7' else (52, 56, 60, 64))
    result[0x4000 + directory_field] = directory_index
    struct.pack_into('<I', result, 0x4000 + flags_field, flags)
    struct.pack_into('<I', result, 0x4000 + location_field, 104)
    raw_url = url.encode() + b'\0'
    result[0x4068:0x4068 + len(raw_url)] = raw_url
    pointer = 104 + len(raw_url)
    struct.pack_into('<I', result, 0x4000 + filename_field, pointer)
    raw_file = filename.encode() + b'\0'
    result[0x4000 + pointer:0x4000 + pointer + len(raw_file)] = raw_file
    return result


class YahooCacheFormatTests(unittest.TestCase):
    def test_allocated_versions_bind_exact_directory_and_literal_filename(self):
        for version in ('4.7', '5.2'):
            row, = yahoo.cache_records(index(version=version))
            self.assertEqual(row['filename'], 'unrelated-cache-name.htm')
            self.assertEqual(row['cache_directory'], 'ABCD1234')
            self.assertEqual(row['cache_size_bytes'], len(html()))
            self.assertEqual(row['cache_directory_locator'], {'byte_offset': 80, 'byte_length': 8})
            self.assertEqual(row['location'], URL)

    def test_no_history_cookies_unallocated_sparse_or_edited_records(self):
        self.assertEqual(list(yahoo.cache_records(index(allocated=False))), [])
        for flags in (0x8, 0x10000, 0x100000, 0x200000):
            self.assertEqual(list(yahoo.cache_records(index(flags=flags))), [])
        self.assertEqual(list(yahoo.cache_records(index(url='Visited:Other@' + URL))), [])

    def test_url_must_be_exact_yahoo_message_endpoint_with_unambiguous_id(self):
        for url in (URL.replace('mail.yahoo.com', 'mail.yahoo.com.evil.test'),
                    URL.replace('https://', 'https://mail.yahoo.com@evil.test/'),
                    URL.replace('/ym/ShowLetter', '/ym/ShowFolder'),
                    URL.replace('MsgId=synthetic-42', 'MsgId='),
                    URL + '&MsgId=other', URL + '&bodyPart=2', URL + '#fragment',
                    URL.replace('/ym/', '/ym/%2e%2e/ym/'), URL.replace('https:', 'file:')):
            with self.subTest(url=url):
                self.assertEqual(list(yahoo.cache_records(index(url=url))), [])
                self.assertIsNone(yahoo.message_content(html(), url))

    def test_directory_table_and_allocation_are_validated(self):
        with self.assertRaisesRegex(ValueError, 'directory'):
            list(yahoo.cache_records(index(directory_index=2)))
        with self.assertRaisesRegex(ValueError, 'component'):
            list(yahoo.cache_records(index(directory='../ABCD1')))
        for name in ('../message.htm', r'..\message.htm', 'message.htm:stream', 'message.htm.'):
            self.assertEqual(list(yahoo.cache_records(index(filename=name))), [])
        data = index()
        data[0x250] = 1
        with self.assertRaisesRegex(ValueError, 'unallocated'):
            list(yahoo.cache_records(data))
        data = index()
        struct.pack_into('<I', data, 72, 2)
        data[92:100] = data[80:88]
        with self.assertRaisesRegex(ValueError, 'ambiguous'):
            list(yahoo.cache_records(data))

    def test_bad_record_string_pointer_length_and_header_do_not_emit_partial_rows(self):
        for data in (index()[:-1], b'not an index' + bytes(0x4400)):
            with self.assertRaises(ValueError):
                list(yahoo.cache_records(data))
        data = index()
        struct.pack_into('<I', data, 0x4034, 0x10000)
        with self.assertRaisesRegex(ValueError, 'string pointer'):
            list(yahoo.cache_records(data))
        data = index()
        struct.pack_into('<I', data, 0x4004, 0)
        with self.assertRaisesRegex(ValueError, 'length'):
            list(yahoo.cache_records(data))

    def test_html_requires_same_message_id_real_headers_and_closed_visible_body(self):
        content = html(body='<p>Exact &amp; synthetic.</p>')
        found = yahoo.message_content(content, URL)
        start, size = found['message_body_byte_offset'], found['message_body_byte_length']
        self.assertEqual(content[start:start + size], b'<div id=message><p>Exact &amp; synthetic.</p></div>')
        self.assertEqual(set(found['message_header_locators']), {'from', 'subject', 'date'})
        for data in (html(message_id='other-id'), html(body=''), html(label='Topic:'),
                     html(body='<script>only script</script>'), html().replace(b'</div>', b''),
                     html().replace(b'name=showLetter', b'name=login'),
                     html().replace(b'</form>', b''),
                     html().replace(b'/ym/ShowLetter?box=Inbox', b'https://evil.test/ym/ShowLetter'),
                     html().replace(b'type=hidden', b'type=text'),
                     b'From: example Subject: example Date: example',
                     b'<html><div id=message>Headerless body</div></html>'):
            with self.subTest(data=data[:60]):
                self.assertIsNone(yahoo.message_content(data, URL))

    def test_quoted_message_markup_in_script_or_comment_is_not_page_structure(self):
        self.assertIsNone(yahoo.message_content(b'<script>' + html() + b'</script>', URL))
        self.assertIsNone(yahoo.message_content(b'<!--' + html() + b'-->', URL))
        self.assertIsNone(yahoo.message_content(b'<template>' + html() + b'</template>', URL))

    def test_mixed_message_forms_or_scattered_headers_are_not_coherent_message(self):
        other_form = (b'<form name=showLetter method=post action="/ym/ShowLetter">'
                      b'<input type=hidden name=MsgId value=other-id></form>')
        self.assertIsNone(yahoo.message_content(other_form + html(), URL))
        scattered = html().replace(b'</tr><tr>', b'</tr></table><table><tr>')
        self.assertIsNone(yahoo.message_content(scattered, URL))
        duplicate = html().replace(b'</table>', b'<tr><td>From:</td><td>other@example.test</td></tr></table>')
        self.assertIsNone(yahoo.message_content(duplicate, URL))
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            yahoo.message_content(html().replace(b'id=message', b'id=other id=message'), URL)


class YahooCacheExtractionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cache = self.root / 'ProfileA' / 'Temporary Internet Files' / 'Content.IE5'
        self.payload = self.cache / 'ABCD1234' / 'unrelated-cache-name.htm'
        self.payload.parent.mkdir(parents=True)
        self.payload.write_bytes(html())
        self.index = self.cache / 'index.dat'
        self.index.write_bytes(index())
        self.ctx = {'examined_at': 987654321, 'common': {'image': 'synthetic.E01', 'exhibit': 'FIX',
                    'source_snapshot': 'base-volume', 'source_variant': 'primary'}}

    def observations(self, paths=None, ctx=None):
        # Interception makes source/negative tests runnable before the central
        # fixed-role catalog lands. The separate integration test uses real emit.
        with patch.object(yahoo, 'emit_attribute') as emit:
            ev = Evidence()
            yahoo.extract(ev, paths or [self.index, self.payload], ctx or self.ctx)
            return emit.call_args_list, ev

    def test_exact_file_and_index_hashes_are_bound_to_scoped_subject(self):
        calls, ev = self.observations()
        self.assertEqual(len(calls), 1)
        args, prov = calls[0]
        self.assertEqual(args[2:5], (yahoo.ROLE, self.payload.name, self.ctx['examined_at']))
        self.assertEqual(json.loads(args[1])[:4], ['synthetic.E01', 'FIX', 'base-volume', 'primary'])
        self.assertEqual(prov['cache_content_sha256'], hashlib.sha256(html()).hexdigest())
        self.assertEqual(prov['index_sha256'], hashlib.sha256(index()).hexdigest())
        self.assertTrue(prov['cache_path'].endswith(r'ABCD1234\unrelated-cache-name.htm'))
        self.assertEqual(prov['byte_offset'], 0x4000)

    def test_changed_index_bytes_do_not_reuse_subject_identity(self):
        before = self.observations()[0][0].args[1]
        changed = index()
        changed[128] = 1  # Uninterpreted header byte still changes source identity.
        self.index.write_bytes(changed)
        after = self.observations()[0][0].args[1]
        self.assertNotEqual(before, after)

    def test_cross_profile_same_basename_or_unindexed_content_does_not_match(self):
        other = self.root / 'ProfileB' / 'Temporary Internet Files' / 'Content.IE5' / 'ABCD1234' / self.payload.name
        other.parent.mkdir(parents=True)
        other.write_bytes(html())
        self.assertEqual(self.observations([self.index, other])[0], [])
        self.assertEqual(self.observations([self.payload])[0], [])
        wrong_directory = self.cache / 'OTHER123' / self.payload.name
        wrong_directory.parent.mkdir()
        wrong_directory.write_bytes(html())
        self.assertEqual(self.observations([self.index, wrong_directory])[0], [])
        self.assertEqual(len(self.observations([self.index, self.payload, other])[0]), 1)

    def test_ambiguous_case_aliases_and_stale_file_sizes_withhold_observation(self):
        self.assertEqual(self.observations([self.index, self.payload, self.payload])[0], [])
        self.payload.write_bytes(html() + b'changed')
        self.assertEqual(self.observations()[0], [])

    def test_scope_missing_or_historical_is_never_promoted(self):
        unknown = {'examined_at': 99, 'common': {'image': 'other', 'exhibit': 'OTHER'}}
        calls, _ = self.observations(ctx=unknown)
        self.assertEqual(json.loads(calls[0].args[1])[:4], ['other', 'OTHER', 'unknown', 'unknown'])
        past = {'examined_at': 99, 'common': dict(self.ctx['common'], source_variant='recovered')}
        calls, _ = self.observations(ctx=past)
        self.assertEqual(calls[0].kwargs['source_variant'], 'recovered')

    def test_new_role_emits_real_typed_attribute_triple(self):
        self.assertTrue(yahoo.ROLE in ROLES, 'central reviewed catalog must be integrated')
        ev = Evidence()
        yahoo.extract(ev, [self.index, self.payload], self.ctx)
        rows = list(ev.rows())
        self.assertEqual(len(rows), 3)
        self.assertEqual({row[0] for row in rows}, {'attributeSubject', ROLES[yahoo.ROLE].kind,
                                                 'attributeTextValue'})
        self.assertEqual({row[1] for row in rows}, {self.ctx['examined_at']})
        self.assertTrue(all(json.loads(row[-1])['timestamp_semantics'] == 'examination_observation' for row in rows))


if __name__ == '__main__':
    unittest.main()
