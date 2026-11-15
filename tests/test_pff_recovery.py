"""Bounded native recovery controls using synthetic properties and subprocesses."""
import base64
import ctypes as C
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from extractor import pff_recovery as pff


COMMON = {'image': 'synthetic-image', 'exhibit': 'synthetic-exhibit',
          'artifact': '/mail/fixture.pst', 'source_snapshot': 'base-volume', 'source_variant': 'primary'}
LIBRARY = {'path': '/synthetic/reviewed.so', 'version': pff.LIBRARY_VERSION, 'sha256': pff.LIBRARY_SHA256}


def property_record(text='Synthetic subject', tag=0x0037, set_index=0, entry_index=0):
    raw = (text + '\0').encode('utf-16-le')
    return {'record_set_index': set_index, 'entry_index': entry_index, 'property_id': tag,
            'value_type': pff.UNICODE, 'raw_bytes': len(raw), 'raw_sha256': pff._sha(raw),
            'raw_base64': base64.b64encode(raw).decode('ascii')}


def response(request, properties=None):
    props = [property_record(), property_record('Synthetic body', 0x1000, entry_index=1)] if properties is None else properties
    layout = [0] * (max((p['record_set_index'] for p in props), default=-1) + 1)
    for prop in props:
        layout[prop['record_set_index']] = max(layout[prop['record_set_index']], prop['entry_index'] + 1)
    return {'format': pff.FORMAT, 'input_sha256': request['input_sha256'], 'library': request['library'],
            'recovery_flags': 0, 'recovered_item_count': 1,
            'items': [{'recovery_index': 0, 'item_identifier': 123, 'item_type': pff.EMAIL_ITEM_TYPE,
                       'properties': props, 'record_set_entry_counts': layout}], 'issues': [], 'skipped_item_types': {},
            'totals': {'record_sets': len(layout), 'entries': sum(layout), 'text_bytes': sum(p['raw_bytes'] for p in props)},
            'resource_limits': {'applied': {}, 'unavailable': ['synthetic']}}


class FakeNative:
    """Opaque handle fixture; exercises traversal, duplicates and cleanup."""
    def __init__(self, sets, item_type=pff.EMAIL_ITEM_TYPE, count=1):
        self.sets, self.item_type, self.count = sets, item_type, count
        self.freed, self.calls = [], []

    def handle(self, name, *args):
        if name == 'file_initialize':
            return 'file'
        if name == 'file_get_recovered_item_by_index':
            return ('item', args[1])
        if name == 'item_get_record_set_by_index':
            return ('set', args[1])
        if name == 'record_set_get_entry_by_index':
            return ('entry', args[0][1], args[1])
        raise AssertionError(name)

    def number(self, name, handle, ctype=None):
        if name == 'file_get_number_of_recovered_items':
            return self.count
        if name == 'item_get_identifier':
            return 123
        if name == 'item_get_type':
            return self.item_type
        if name == 'item_get_number_of_record_sets':
            return len(self.sets)
        if name == 'record_set_get_number_of_entries':
            return len(self.sets[handle[1]])
        entry = self.sets[handle[1]][handle[2]]
        return {'record_entry_get_entry_type': entry[0], 'record_entry_get_value_type': entry[1],
                'record_entry_get_data_size': len(entry[2])}[name]

    def call(self, name, *args, **kwargs):
        self.calls.append((name, args, kwargs))
        if name == 'record_entry_get_data':
            handle, buffer, size = args
            raw = self.sets[handle[1]][handle[2]][2]
            buffer[:size] = raw

    def free(self, kind, handle):
        self.freed.append((kind, handle))


def raw_entry(text='Synthetic text', tag=0x0037, value_type=pff.UNICODE):
    return tag, value_type, (text + '\0').encode('utf-16-le')


class NativeTraversal(unittest.TestCase):
    def run_native(self, fake, limits=None):
        with patch.object(pff, 'Native', return_value=fake):
            return pff._recover_native('/read-only/fixture.pst', LIBRARY, limits or pff.Limits())

    def test_exact_unicode_properties_and_owned_handle_cleanup(self):
        fake = FakeNative([[raw_entry('Résumé'), raw_entry('Body\r\n', 0x1000)]])
        result = self.run_native(fake)
        self.assertEqual(result['recovered_item_count'], 1)
        props = result['items'][0]['properties']
        self.assertEqual(props[0]['raw_sha256'], hashlib.sha256(raw_entry('Résumé')[2]).hexdigest())
        self.assertEqual(props[1]['entry_index'], 1)
        self.assertEqual([k for k, _ in fake.freed], ['record_entry', 'record_entry', 'record_set', 'item', 'file'])
        self.assertEqual(next(args[1] for name, args, _ in fake.calls if name == 'file_recover_items'), 0)
        self.assertEqual(next(args[2] for name, args, _ in fake.calls if name == 'file_open'), 1)
        self.assertEqual(next(kw['expected'] for name, _, kw in fake.calls if name == 'file_close'), 0)

    def test_duplicate_properties_same_set_or_other_set_reject_whole_item(self):
        for sets in ([[raw_entry(), raw_entry()]], [[raw_entry()], [raw_entry()]],
                     [[raw_entry(), raw_entry(value_type=0x001E)]]):
            with self.subTest(sets=len(sets)):
                result = self.run_native(FakeNative(sets))
                self.assertEqual(result['items'], [])
                self.assertIn('duplicate', result['issues'][0]['reason'])

    def test_ansi_invalid_unicode_and_ambiguous_nuls_do_not_emit(self):
        for entry in (raw_entry(value_type=0x001E), (0x0037, pff.UNICODE, b'\x00'),
                      (0x0037, pff.UNICODE, b'\x00\xd8'), raw_entry('a\0b'), raw_entry('a\0')):
            result = self.run_native(FakeNative([[entry]]))
            self.assertEqual(result['items'], [])
            self.assertEqual(len(result['issues']), 1)

    def test_literal_empty_and_missing_properties_are_different(self):
        empty = self.run_native(FakeNative([[(0x0037, pff.UNICODE, b'')]]))
        missing = self.run_native(FakeNative([[(0x1111, pff.UNICODE, b'')]]))
        self.assertEqual(len(empty['items'][0]['properties']), 1)
        self.assertEqual(empty['items'][0]['properties'][0]['raw_bytes'], 0)
        self.assertEqual(missing['items'][0]['properties'], [])

    def test_non_email_items_are_counted_without_message_interpretation(self):
        for kind in (0, 12, 255):
            result = self.run_native(FakeNative([[raw_entry()]], item_type=kind))
            self.assertEqual(result['items'], [])
            self.assertEqual(result['skipped_item_types'], {str(kind): 1})

    def test_count_and_byte_budgets_fail_closed_and_free_handles(self):
        for fake, limits in ((FakeNative([], count=-1), pff.Limits()),
                             (FakeNative([], count=2), replace(pff.Limits(), items=1)),
                             (FakeNative([[], []]), replace(pff.Limits(), record_sets_per_item=1)),
                             (FakeNative([[raw_entry(), raw_entry(tag=0x1000)]]), replace(pff.Limits(), entries_per_set=1)),
                             (FakeNative([[raw_entry()]]), replace(pff.Limits(), property_bytes=2)),
                             (FakeNative([[raw_entry('abc'), raw_entry('abc', 0x1000)]]), replace(pff.Limits(), property_bytes=8, text_bytes=8))):
            with self.subTest(limits=limits):
                with self.assertRaises(pff.RecoveryError):
                    self.run_native(fake, limits)
                self.assertEqual(fake.freed[-1][0], 'file')

    def test_repeated_item_identifier_keeps_distinct_recovery_indices(self):
        result = self.run_native(FakeNative([[raw_entry()]], count=2))
        self.assertEqual([i['item_identifier'] for i in result['items']], [123, 123])
        self.assertEqual([i['recovery_index'] for i in result['items']], [0, 1])


class ResponseBoundary(unittest.TestCase):
    def setUp(self):
        self.request = {'input_sha256': 'a' * 64, 'library': LIBRARY}
        self.valid = response(self.request)

    def validate(self, value):
        return pff._validate_response(pff._json(value), self.request, pff.Limits())

    def test_independent_raw_hash_and_strict_unicode_decode(self):
        result = self.validate(self.valid)
        self.assertEqual(result['items'][0]['properties'][0]['value'], 'Synthetic subject')
        self.assertEqual(result['items'][0]['properties'][1]['value'], 'Synthetic body')

    def test_corrupt_identity_encoding_index_counts_and_duplicates_rejected(self):
        def modify(key, value):
            return lambda d: d.update({key: value})
        mutations = [modify('input_sha256', 'b' * 64), modify('recovery_flags', 1),
                     modify('recovery_flags', False), modify('recovered_item_count', -1),
                     modify('recovered_item_count', 2),
                     lambda d: d['items'].append(dict(d['items'][0])),
                     lambda d: d['items'][0].update(item_type=12),
                     lambda d: d['items'][0].update(item_identifier=True),
                     lambda d: d['items'][0]['properties'][0].update(raw_sha256='0'*64),
                     lambda d: d['items'][0]['properties'][0].update(raw_base64='not base64'),
                     lambda d: d['items'][0]['properties'][0].update(value_type=0x1E),
                     lambda d: d['items'][0]['properties'][0].update(record_set_index=-1),
                     lambda d: d['items'][0]['properties'][1].update(property_id=0x0037),
                     lambda d: d['items'][0]['properties'][1].update(entry_index=0),
                     lambda d: d['items'][0]['properties'][0].update(entry_index=999),
                     lambda d: d['items'][0].update(record_set_entry_counts=[True]),
                     lambda d: d['totals'].update(record_sets=0),
                     lambda d: d['totals'].update(entries=0),
                     lambda d: d['totals'].update(text_bytes=0)]
        for mutation in mutations:
            candidate = json.loads(json.dumps(self.valid))
            mutation(candidate)
            with self.subTest(candidate=str(candidate)[:100]), self.assertRaises(pff.RecoveryError):
                self.validate(candidate)

    def test_duplicate_json_keys_truncation_and_oversize_rejected(self):
        for data in (b'{"format":1,"format":2}', pff._json(self.valid)[:-3],
                     b' ' * (pff.Limits().output_bytes // 2 + 1)):
            with self.assertRaises(pff.RecoveryError):
                pff._validate_response(data, self.request, pff.Limits())

    def test_examination_time_and_all_scope_axes_are_bound(self):
        parsed = self.validate(self.valid)
        baseline = pff._evidence(parsed, COMMON, '/mail/fixture.pst', 'a'*64, 123456)
        subjects = {row[4] for row in baseline.rows() if row[0] == 'attributeSubject'}
        self.assertEqual(len(subjects), 1)
        for row in baseline.rows():
            self.assertEqual(row[1], 123456)
            prov = json.loads(row[5])
            self.assertEqual(prov['source_variant'], 'parser-recovery')
            self.assertEqual(prov['input_source_variant'], 'primary')
            self.assertEqual(prov['source_snapshot'], 'base-volume')
            self.assertNotIn('physical_byte_offset', prov['property_locator'])
        for key, value in [('image', 'another'), ('exhibit', 'another'), ('source_snapshot', 'unknown'),
                           ('source_variant', 'backup')]:
            common = dict(COMMON, **{key: value})
            changed = pff._evidence(parsed, common, '/mail/fixture.pst', 'a'*64, 123456)
            self.assertTrue(subjects.isdisjoint(row[4] for row in changed.rows() if row[0]=='attributeSubject'))
        unknown = pff._evidence(parsed, {'image': 'i', 'exhibit': 'e'}, '/p', 'a'*64, 1)
        self.assertTrue(all(json.loads(r[5])['source_snapshot']=='unknown' for r in unknown.rows()))
        self.assertTrue(all(json.loads(r[5])['input_source_variant']=='unknown' for r in unknown.rows()))

    def test_record_sets_are_separate_subjects_and_empty_is_literal(self):
        self.valid = response(self.request, [property_record('', set_index=0),
                                            property_record('body', 0x1000, set_index=1)])
        ev = pff._evidence(self.validate(self.valid), COMMON, '/mail.pst', 'a'*64, 1)
        self.assertEqual(len({r[4] for r in ev.rows() if r[0]=='attributeSubject'}), 2)
        self.assertIn('""', [r[4] for r in ev.rows() if r[0]=='attributeTextValue'])


class ProcessAndCapture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'fixture.pst'
        self.source.write_bytes(b'!BDN' + b'\0' * 1020)

    @staticmethod
    def worker(request_path, output_dir, limits):
        request = json.loads(request_path.read_bytes())
        data = pff._json(response(request))
        (output_dir / 'worker.json').write_bytes(data)
        (output_dir / 'worker.stderr').write_bytes(b'')
        return data

    def test_success_writes_source_bound_typed_facts_and_refuses_existing_output(self):
        before = self.source.read_bytes()
        out = self.root / 'result'
        with patch.object(pff, 'library_identity', return_value=LIBRARY), patch.object(pff, '_run_worker', self.worker):
            receipt = pff.recover_file(self.source, out, COMMON, 123456)
            with self.assertRaises(FileExistsError):
                pff.recover_file(self.source, out, COMMON, 123456)
        self.assertEqual(receipt['status'], 'completed')
        self.assertEqual(receipt['attributes'], 2)
        self.assertEqual(receipt['input_sha256'], hashlib.sha256(before).hexdigest())
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(hashlib.sha256((out/'facts.json').read_bytes()).hexdigest(), receipt['facts_sha256'])
        self.assertEqual(len(json.loads((out/'facts.json').read_bytes())['facts']), 6)

    def test_failed_subprocess_or_invalid_response_writes_no_facts(self):
        for index, effect in enumerate((pff.RecoveryError('native crash'), b'{"broken":true}')):
            out = self.root / str(index)
            options = {'side_effect': effect} if isinstance(effect, Exception) else {'return_value': effect}
            with patch.object(pff, 'library_identity', return_value=LIBRARY), patch.object(pff, '_run_worker', **options):
                with self.assertRaises(pff.RecoveryError):
                    pff.recover_file(self.source, out, COMMON, 1)
            receipt = json.loads((out/'receipt.json').read_bytes())
            self.assertEqual(receipt['status'], 'failed')
            self.assertEqual(receipt['attributes'], 0)
            self.assertFalse((out/'facts.json').exists())

    def test_input_type_signature_size_and_library_pin_fail_closed(self):
        bad = self.root / 'bad'
        bad.write_bytes(b'not a PFF')
        link = self.root / 'link'
        link.symlink_to(self.source)
        for index, (source, limits) in enumerate(((bad, pff.Limits()), (link, pff.Limits()),
                                                  (self.source, replace(pff.Limits(), input_bytes=2)))):
            with self.subTest(source=source), self.assertRaises(pff.RecoveryError):
                pff.recover_file(source, self.root / ('invalid'+str(index)), COMMON, 1, limits=limits)
        with patch.object(pff, '_file_hash', return_value='0'*64), self.assertRaises(pff.RecoveryError):
            pff.library_identity()

    def test_changed_capture_and_aggregate_output_budget_fail_without_facts(self):
        def changed(request_path, output_dir, limits):
            data = self.worker(request_path, output_dir, limits)
            captured = output_dir / 'source.pff'
            captured.chmod(0o600)
            captured.write_bytes(b'changed')
            return data
        for name, worker, common, limits in (
                ('changed', changed, COMMON, pff.Limits()),
                ('aggregate', self.worker, dict(COMMON, additional_capture_detail='X'*3000),
                 replace(pff.Limits(), output_bytes=16384))):
            out = self.root / name
            with patch.object(pff, 'library_identity', return_value=LIBRARY), patch.object(pff, '_run_worker', worker):
                with self.assertRaises(pff.RecoveryError):
                    pff.recover_file(self.source, out, common, 1, limits=limits)
            receipt = json.loads((out/'receipt.json').read_bytes())
            self.assertEqual(receipt['status'], 'failed')
            self.assertFalse((out/'facts.json').exists())
            self.assertNotIn('facts_sha256', receipt)

    def test_actual_invalid_native_file_is_isolated_and_produces_failed_receipt(self):
        # Calls the real reviewed library against synthetic invalid PFF bytes only.
        try:
            pff.library_identity()
        except pff.RecoveryError:
            self.skipTest('reviewed native library not installed on this platform')
        with self.assertRaises(pff.RecoveryError):
            pff.recover_file(self.source, self.root/'native-invalid', COMMON, 1)
        receipt = json.loads((self.root/'native-invalid'/'receipt.json').read_bytes())
        self.assertEqual(receipt['status'], 'failed')
        self.assertFalse((self.root/'native-invalid'/'facts.json').exists())

    def test_wall_timeout_kills_and_reaps_subprocess(self):
        out = self.root / 'timeout'
        out.mkdir()
        process = unittest.mock.Mock(pid=12345)
        process.wait.side_effect = [subprocess.TimeoutExpired('native', 1), -9]
        with patch.object(pff.subprocess, 'Popen', return_value=process), patch.object(pff.os, 'killpg') as kill:
            with self.assertRaisesRegex(pff.RecoveryError, 'wall-clock'):
                pff._run_worker(out/'request.json', out, replace(pff.Limits(), wall_seconds=1))
        kill.assert_called_once_with(12345, pff.signal.SIGKILL)
        self.assertEqual(process.wait.call_count, 2)

    def test_child_crash_and_oversize_output_rejected(self):
        for name, returncode, size in [('crash', -11, 0), ('oversize', 0, 8193)]:
            out = self.root / name
            out.mkdir()
            def process(*args, **kwargs):
                kwargs['stdout'].write(b'X' * size)
                return unittest.mock.Mock(wait=unittest.mock.Mock(return_value=returncode))
            with patch.object(pff.subprocess, 'Popen', side_effect=process), self.assertRaises(pff.RecoveryError):
                pff._run_worker(out/'request.json', out, replace(pff.Limits(), output_bytes=16384))

    def test_timeout_exit_race_still_reaps_child(self):
        out = self.root / 'exit-race'
        out.mkdir()
        process = unittest.mock.Mock(pid=12345)
        process.wait.side_effect = [subprocess.TimeoutExpired('native', 1), 0]
        with patch.object(pff.subprocess, 'Popen', return_value=process), \
                patch.object(pff.os, 'killpg', side_effect=ProcessLookupError):
            with self.assertRaisesRegex(pff.RecoveryError, 'wall-clock'):
                pff._run_worker(out/'request.json', out, replace(pff.Limits(), wall_seconds=1))
        self.assertEqual(process.wait.call_count, 2)

    def test_native_function_abis_are_explicit_and_version_checked(self):
        fake = unittest.mock.Mock()
        fake.libpff_get_version.return_value = pff.LIBRARY_VERSION.encode()
        with patch.object(pff, '_file_hash', return_value=pff.LIBRARY_SHA256), patch.object(pff.C, 'CDLL', return_value=fake):
            native = pff.Native(LIBRARY)
        self.assertEqual(native.lib.libpff_file_recover_items.argtypes[1], C.c_uint8)
        self.assertEqual(native.lib.libpff_record_entry_get_data_size.argtypes[1], C.POINTER(C.c_size_t))
        self.assertEqual(native.lib.libpff_item_get_identifier.argtypes[1], C.POINTER(C.c_uint32))
        self.assertIs(native.lib.libpff_error_free.restype, None)

    def test_limits_reject_bool_negative_and_invalid_budgets(self):
        for change in ({'items': True}, {'cpu_seconds': -1}, {'output_bytes': 1},
                       {'text_bytes': 1, 'property_bytes': 2}):
            with self.assertRaises(ValueError):
                replace(pff.Limits(), **change)


if __name__ == '__main__':
    unittest.main()
