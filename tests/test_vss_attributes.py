"""VSS catalog attributes from synthetic volume bytes, without snapshot content."""
from contextlib import ExitStack
import io
import json
import struct
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
import uuid

from extractor import filetraces as ft

try:
    from dissect.volume.vss import VSS
except ImportError:
    VSS = None


COPY = uuid.UUID('5bf388b1-c675-492b-af9c-4a7751077fc2')
SET = uuid.UUID('755e0434-93ce-4c82-bdd0-d8f669b1be82')
STORE = uuid.UUID('26976077-d5d4-4313-9fa6-dc2bb2f47138')
CREATED = 133444736001234560
EXAMINED = 1800000000000000
FILE_REFERENCE = (3 << 48) | 42
COMMON = dict(image='synthetic.E01', exhibit='SYNTHETIC',
              source_snapshot='base-volume', source_variant='primary')
VSS_ID = uuid.UUID('3808876b-c176-4e48-b7ae-04046e6cc752').bytes_le


class Collector:
    def __init__(self):
        self.rows, self.problems = [], []

    def add(self, kind, t, res, obj, aux='', **prov):
        self.rows.append(dict(kind=kind, t=t, obj=obj, aux=aux, prov=prov))

    def problem(self, source, error):
        self.problems.append((source, str(error)))


def volume_bytes(*, copy_id=COPY, set_id=SET, store_id=STORE, created=CREATED):
    """Minimal real Dissect-readable metadata; deliberately no NTFS snapshot."""
    data = bytearray(0xc000)
    data[0x1e00:0x1e10] = VSS_ID
    struct.pack_into('<IIQQQQ', data, 0x1e10, 1, 1, 0x1e00, 0, 0, 0x4000)
    data[0x4000:0x4010] = VSS_ID
    struct.pack_into('<IIQQQ', data, 0x4010, 1, 2, 0, 0x4000, 0)
    struct.pack_into('<QQ16sQQQ72s', data, 0x4080, 2, 987654321,
                     store_id.bytes_le, 0, 0, created, bytes(72))
    struct.pack_into('<QQ16s7Q40s', data, 0x4100, 3, 0, store_id.bytes_le,
                     0x8000, 0, 0, FILE_REFERENCE, 1234567, 0, 0, bytes(40))
    data[0x8000:0x8010] = VSS_ID
    struct.pack_into('<IIQQQQ', data, 0x8010, 1, 4, 0, 0x8000, 0, 0x4000)
    info = bytes(16) + copy_id.bytes_le + set_id.bytes_le + struct.pack('<4I', 1, 1, 0, 0)
    machine = 'SYNTHETIC'.encode('utf-16-le')
    info += (struct.pack('<H', len(machine)) + machine) * 2
    data[0x8080:0x8080 + len(info)] = info
    return bytes(data)


def metadata_ntfs(store_id=STORE, *, sequence=3, flags=1, filename=None, reparse=False):
    path = filename or 'System Volume Information\\{' + str(store_id) + '}{3808876b-c176-4e48-b7ae-04046e6cc752}'
    record = NS(segment=42, header=NS(SequenceNumber=sequence, Flags=flags),
                is_file=lambda: True, is_reparse_point=lambda: reparse, full_paths=lambda: [path])
    return NS(mft=NS(get=lambda segment: record))


@unittest.skipIf(VSS is None, 'Dissect VSS parser not installed')
class VssCatalogAttributes(unittest.TestCase):
    def read_attributes(self, *, common=None, data=None, examined_at=EXAMINED):
        vss = VSS(io.BytesIO(data or volume_bytes()))
        ev = Collector()
        ft._vss_catalog_attributes(ev, vss, vss.catalog.stores[0], 'C:', 'SERIAL',
                                   COMMON if common is None else common, examined_at,
                                   ntfs=metadata_ntfs(uuid.UUID(bytes_le=bytes(vss.catalog.stores[0].desc2.store_identifier))))
        return ev, vss

    def test_four_values_bind_one_catalog_subject_with_exam_time(self):
        ev, _ = self.read_attributes()
        subjects = [row['aux'] for row in ev.rows if row['kind'] == 'attributeSubject']
        values = {row['prov']['attribute_role']: json.loads(row['aux']) for row in ev.rows
                  if row['kind'] == 'attributeTextValue'}
        self.assertEqual(len(ev.rows), 12)
        self.assertEqual(len(set(subjects)), 1)
        self.assertEqual(values, {
            'vss.copy_id': '{' + str(COPY) + '}',
            'vss.set_id': '{' + str(SET) + '}',
            'vss.storage_path': 'C:\\System Volume Information\\{' + str(STORE)
                                + '}{3808876b-c176-4e48-b7ae-04046e6cc752}',
            'vss.created_at': ft.iso(ft.us_from_filetime(CREATED)),
        })
        self.assertTrue(all(row['t'] == EXAMINED for row in ev.rows))
        self.assertNotEqual(EXAMINED, ft.us_from_filetime(CREATED))
        for row in ev.rows:
            self.assertEqual(row['prov']['source_snapshot'], 'base-volume')
            self.assertEqual(row['prov']['source_variant'], 'primary')
            self.assertEqual(row['prov']['catalog_offset'], 0x4000)
            self.assertEqual(row['prov']['store_header_offset'], 0x8000)
            self.assertEqual(row['prov']['timestamp_semantics'], 'examination_observation')
        # Volume size and allocated metadata size are intentionally not copy size.
        self.assertFalse(any('size' in role for role in values))

    def test_metadata_survives_unreadable_snapshot_content(self):
        ev = Collector()
        fs = NS(ntfs=metadata_ntfs(), volume=io.BytesIO(volume_bytes()))
        with patch.object(ft, '_ntfs_volumes', return_value=[('C:', 'SERIAL', fs)]), \
             patch.object(ft, '_journal', return_value=None), \
             patch('dissect.ntfs.NTFS', side_effect=ValueError('synthetic snapshot absent')):
            ft._shadow_copies(ev, NS(), '', COMMON, examined_at=EXAMINED)
        self.assertEqual(sum(row['kind'] == 'attributeSubject' for row in ev.rows), 4)
        self.assertEqual(sum(row['kind'] == 'shadowCopy' for row in ev.rows), 1)
        self.assertFalse(any(row['kind'] == 'fileSeen' for row in ev.rows))
        self.assertEqual(len(ev.problems), 1)
        self.assertIn('synthetic snapshot absent', ev.problems[0][1])

    def test_creation_value_retains_submicrosecond_filetime_precision(self):
        ev, _ = self.read_attributes(data=volume_bytes(created=CREATED + 7))
        value, = [json.loads(row['aux']) for row in ev.rows if row['kind'] == 'attributeTextValue'
                   and row['prov']['attribute_role'] == 'vss.created_at']
        self.assertEqual(value, ft.iso(ft.us_from_filetime(CREATED))[:-1] + '7Z')
        self.assertTrue(all(row['prov']['catalog_creation_filetime'] == CREATED + 7 for row in ev.rows))

    def test_subject_separates_copies_sets_volume_and_all_scope_axes(self):
        original, _ = self.read_attributes()
        subject = original.rows[0]['aux']
        changed_inputs = [dict(data=volume_bytes(copy_id=uuid.UUID(int=9))),
                          dict(data=volume_bytes(set_id=uuid.UUID(int=10))),
                          dict(data=volume_bytes(store_id=uuid.UUID(int=11)))]
        for axis, value in [('image', 'other.E01'), ('exhibit', 'OTHER'),
                            ('source_snapshot', 'vss:' + str(COPY)), ('source_variant', 'recovered')]:
            changed_inputs.append(dict(common=dict(COMMON, **{axis: value})))
        for args in changed_inputs:
            with self.subTest(args=args.keys()):
                changed, _ = self.read_attributes(**args)
                self.assertNotEqual(changed.rows[0]['aux'], subject)

    def test_unknown_and_nonprimary_origin_are_not_promoted(self):
        for common, expected in [(dict(image='x', exhibit='Y'), ('unknown', 'unknown')),
                                 (dict(COMMON, source_variant='recovered'), ('base-volume', 'recovered'))]:
            before = dict(common)
            ev, _ = self.read_attributes(common=common)
            self.assertEqual(common, before)
            self.assertTrue(all((row['prov']['source_snapshot'], row['prov']['source_variant']) == expected
                                for row in ev.rows))

    def test_invalid_join_time_or_locator_emits_no_partial_attributes(self):
        mutations = [lambda store: setattr(store.desc3, 'store_identifier', uuid.UUID(int=90).bytes_le),
                     lambda store: setattr(store.desc2, 'creation_time', 2**64 - 1),
                     lambda store: setattr(store.desc3, 'store_header_offset', 0),
                     lambda store: setattr(store, 'copy_identifier', 'not-a-guid')]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                vss = VSS(io.BytesIO(volume_bytes()))
                store = vss.catalog.stores[0]
                mutate(store)
                ev = Collector()
                with self.assertRaises((ValueError, OverflowError)):
                    ft._vss_catalog_attributes(ev, vss, store, 'C:', 'SERIAL', COMMON, EXAMINED)
                self.assertEqual(ev.rows, [])

    def test_no_examination_time_is_invented(self):
        ev, _ = self.read_attributes(examined_at=None)
        self.assertEqual(ev.rows, [])
        for stamp in (0, -1, True, '2026-01-01'):
            with self.subTest(stamp=stamp), self.assertRaises(ValueError):
                self.read_attributes(examined_at=stamp)

    def test_unresolved_reused_or_wrong_metadata_file_does_not_invent_path(self):
        for ntfs in (None, metadata_ntfs(sequence=4), metadata_ntfs(flags=0),
                     metadata_ntfs(reparse=True), metadata_ntfs(filename='unrelated.txt')):
            with self.subTest(ntfs=ntfs):
                vss = VSS(io.BytesIO(volume_bytes()))
                ev = Collector()
                ft._vss_catalog_attributes(ev, vss, vss.catalog.stores[0], 'C:', 'SERIAL',
                                           COMMON, EXAMINED, ntfs=ntfs)
                roles = {row['prov']['attribute_role'] for row in ev.rows}
                self.assertEqual(roles, {'vss.copy_id', 'vss.set_id', 'vss.created_at'})
                self.assertEqual(len(ev.rows), 9)
                self.assertEqual(len(ev.problems), 0 if ntfs is None else 1)

    def test_same_name_in_different_record_does_not_supply_storage_path(self):
        vss = VSS(io.BytesIO(volume_bytes()))
        ntfs = metadata_ntfs()
        record = ntfs.mft.get(42)
        ntfs.mft.get = lambda key: record if isinstance(key, int) else NS(segment=99, header=record.header)
        ev = Collector()
        ft._vss_catalog_attributes(ev, vss, vss.catalog.stores[0], 'C:', 'SERIAL',
                                   COMMON, EXAMINED, ntfs=ntfs)
        self.assertNotIn('vss.storage_path', {row['prov']['attribute_role'] for row in ev.rows})
        self.assertIn('different NTFS file reference', ev.problems[0][1])

    def test_entrypoint_passes_actual_examination_time(self):
        ev = Collector()
        with ExitStack() as stack:
            for name in ('_registry', '_thumbnail_caches', '_spool_files', '_print_log'):
                stack.enter_context(patch.object(ft, name))
            stack.enter_context(patch.object(ft, '_search_index', return_value={}))
            stack.enter_context(patch.object(ft, '_spool_dir', return_value=''))
            shadow = stack.enter_context(patch.object(ft, '_shadow_copies'))
            ft.extract(ev, NS(timezone='UTC'), dict(common=COMMON, examined_at=EXAMINED))
        shadow.assert_called_once_with(ev, unittest.mock.ANY, '', COMMON, examined_at=EXAMINED)
        self.assertEqual(ev.problems, [])


if __name__ == '__main__':
    unittest.main()
