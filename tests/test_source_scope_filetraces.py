"""Reader byte origins remain separate from referenced shadow-copy objects."""
from contextlib import ExitStack
from types import ModuleType, SimpleNamespace as NS
import unittest
from unittest.mock import patch
import uuid

from extractor import filetraces as ft


BASE_FT = 130717152000000000
SERIAL = 0x12345678CA0C7A48
COPY_IDS = (uuid.UUID('AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE'),
            uuid.UUID('11111111-2222-3333-4444-555555555555'))
COMMON = {'image': 'workstation.E01', 'exhibit': 'WORKSTATION', 'tool': 'synthetic'}


class Collector:
    def __init__(self):
        self.rows, self.problems = [], []

    def add(self, kind, t, res, obj, aux='', **prov):
        self.rows.append({'kind': kind, 't': t, 'obj': obj, 'aux': aux, 'prov': prov})

    def problem(self, source, error):
        self.problems.append((source, type(error).__name__, str(error)))


def journal_ntfs(usn, name='same.txt'):
    def ref(record, sequence):
        return NS(SegmentNumberLowPart=record, SegmentNumberHighPart=0, SequenceNumber=sequence)
    rec = NS(filename=name, record=NS(Usn=usn, TimeStamp=BASE_FT + usn * 10_000_000,
             Reason=ft.USN_FILE_CREATE | ft.USN_CLOSE,
             FileReferenceNumber=ref(40, 2), ParentFileReferenceNumber=ref(5, 1)))
    root = NS(header=NS(SequenceNumber=1), full_path=lambda: '')
    return NS(serial=SERIAL, mft=lambda _number: root,
              usnjrnl=NS(records=lambda: iter([rec])))


class FileTraceSourceScope(unittest.TestCase):
    def run_shadow_reader(self, *, variant='primary'):
        base = journal_ntfs(100)
        snapshots = [journal_ntfs(10), journal_ntfs(20)]
        stores = []
        for index, copy_id in enumerate(COPY_IDS):
            stores.append(NS(copy_identifier=copy_id, copy_set_identifier=uuid.UUID(int=3),
                             desc2=NS(store_identifier=uuid.UUID(int=index + 4).bytes_le),
                             creation_time=BASE_FT + (index + 1) * 1_000_000_000,
                             information=NS(operating_machine='host', service_machine='host', attributes='0'),
                             open=lambda index=index: snapshots[index]))
        ntfs_module, vss_module = ModuleType('dissect.ntfs'), ModuleType('dissect.volume.vss')
        ntfs_module.NTFS = lambda stream: stream
        vss_module.VSS = lambda _volume: NS(catalog=NS(stores=stores))
        modules = {'dissect': ModuleType('dissect'), 'dissect.ntfs': ntfs_module,
                   'dissect.volume': ModuleType('dissect.volume'), 'dissect.volume.vss': vss_module}
        path = r'Users\analyst\same.txt'
        old_row = (path, 10, BASE_FT, BASE_FT - 10_000_000, BASE_FT, BASE_FT)
        live_row = (path, 20, BASE_FT + 10_000_000, BASE_FT - 10_000_000, BASE_FT, BASE_FT)
        common = dict(COMMON, source_snapshot='base-volume', source_variant=variant)
        original_common = dict(common)
        ev = Collector()
        with patch.dict('sys.modules', modules), \
             patch.object(ft, '_ntfs_volumes', return_value=[('C:', 'CA0C7A48', NS(ntfs=base, volume='base bytes'))]), \
             patch.object(ft, '_tree', side_effect=lambda ntfs: ({path.lower(): live_row if ntfs is base else old_row}, [])):
            ft._shadow_copies(ev, NS(), '', common)
        self.assertEqual(common, original_common)
        self.assertEqual(ev.problems, [])
        return ev

    def test_base_catalog_and_each_snapshot_have_distinct_byte_origins(self):
        ev = self.run_shadow_reader()
        creations = [row for row in ev.rows if row['kind'] == 'fileCreationRecorded']
        self.assertEqual([row['prov']['source_snapshot'] for row in creations],
                         ['base-volume'] + ['vss:' + str(copy_id) for copy_id in COPY_IDS])
        self.assertEqual({row['prov']['source_variant'] for row in ev.rows}, {'primary'})
        # Same image, volume, file identity and filename do not imply one source snapshot.
        self.assertEqual({row['obj'] for row in creations}, {'same.txt'})
        self.assertEqual({row['prov']['file_record'] for row in creations}, {40})
        self.assertEqual(len({row['prov']['source_snapshot'] for row in creations}), 3)
        catalogs = [row for row in ev.rows if row['kind'] == 'shadowCopy']
        self.assertEqual([row['obj'] for row in catalogs], ['{' + str(copy_id) + '}' for copy_id in COPY_IDS])
        self.assertTrue(all(row['prov']['source_snapshot'] == 'base-volume' for row in catalogs))

    def test_tree_rows_retain_vss_origin_and_label_base_comparison_context(self):
        ev = self.run_shadow_reader()
        rows = [row for row in ev.rows if row['kind'] == 'fileSeen']
        self.assertEqual({row['prov']['source_snapshot'] for row in rows},
                         {'vss:' + str(copy_id) for copy_id in COPY_IDS})
        self.assertTrue(rows)
        for row in rows:
            self.assertEqual(row['prov']['source_path'], r'C:\Users\analyst')
            self.assertEqual(row['prov']['source_stream'], '$I30')
            self.assertEqual(row['prov']['source_record_type'], 'directory FILE_NAME index entry')
            self.assertEqual(row['prov']['live_comparison_source']['source_snapshot'], 'base-volume')
            self.assertEqual(row['prov']['live_comparison_source']['source_variant'], 'primary')
            self.assertEqual(row['prov']['size'], 10)
            self.assertEqual(row['prov']['live_size'], 20)
            self.assertIn(row['prov']['shadow_copy'].strip('{}'), row['prov']['source_snapshot'])
            time_source = row['prov']['timestamp_source']
            if row['prov']['time_meaning'].startswith('creation time of the shadow copy:'):
                self.assertEqual(time_source['source_snapshot'], 'base-volume')
                self.assertEqual(time_source['field'], 'VSS catalog creation_time')
            else:
                self.assertEqual(time_source['source_snapshot'], row['prov']['source_snapshot'])
                self.assertEqual(time_source['source_stream'], '$I30')

    def test_reference_equality_does_not_establish_equal_source_snapshot(self):
        ev = self.run_shadow_reader()
        names = [row for row in ev.rows if row['kind'] == 'journalName']
        # The reference key intentionally permits historical comparison. Selected
        # single-view answers still require the separate origin of every row.
        self.assertEqual(len(names), 3)
        self.assertEqual(len({row['aux'] for row in names}), 1)
        self.assertEqual(len({row['prov']['source_snapshot'] for row in names}), 3)

    def test_explicit_nonprimary_variant_is_not_promoted_by_snapshot_propagation(self):
        ev = self.run_shadow_reader(variant='recovered')
        self.assertEqual({row['prov']['source_variant'] for row in ev.rows}, {'recovered'})
        for row in ev.rows:
            comparison = row['prov'].get('live_comparison_source')
            if comparison:
                self.assertEqual(comparison['source_variant'], 'recovered')

    def test_referenced_copy_metadata_does_not_reclassify_direct_journal_source(self):
        ev = Collector()
        common = dict(COMMON, source_snapshot='base-volume', source_variant='primary')
        ft._journal(ev, journal_ntfs(100), 'C:', '', common, shadow_copy='{' + str(COPY_IDS[0]) + '}')
        self.assertTrue(ev.rows)
        self.assertTrue(all(row['prov']['source_snapshot'] == 'base-volume' for row in ev.rows))

    def test_entrypoint_preserves_explicit_primary_origin_without_mutating_context(self):
        common = dict(COMMON, source_snapshot='base-volume', source_variant='primary')
        before = dict(common)
        received = []
        search_options = []
        def search(*args, **kwargs):
            received.append(dict(args[-1]))
            search_options.append(kwargs)
            return {}
        with ExitStack() as stack:
            for name in ('_registry', '_thumbnail_caches', '_shadow_copies', '_spool_files', '_print_log'):
                stack.enter_context(patch.object(ft, name, side_effect=lambda *args: received.append(dict(args[-1]))))
            stack.enter_context(patch.object(ft, '_search_index', side_effect=search))
            stack.enter_context(patch.object(ft, '_spool_dir', return_value=''))
            ft.extract(Collector(), NS(timezone='UTC'), {'common': common})
        self.assertEqual(common, before)
        self.assertEqual(len(received), 6)
        self.assertEqual(search_options, [{'examined_at': None}])
        self.assertTrue(all(prov['source_snapshot'] == 'base-volume' for prov in received))
        self.assertTrue(all(prov['source_variant'] == 'primary' for prov in received))

    def test_unscoped_direct_call_is_unknown_not_assumed_primary(self):
        ev = Collector()
        ft._journal(ev, journal_ntfs(100), 'C:', '', COMMON)
        self.assertTrue(ev.rows)
        self.assertTrue(all(row['prov']['source_snapshot'] == 'unknown' for row in ev.rows))
        self.assertTrue(all(row['prov']['source_variant'] == 'unknown' for row in ev.rows))

    def test_specific_read_scope_overrides_common_defaults_without_mutating_them(self):
        ev = Collector()
        common = dict(COMMON, source_snapshot='base-volume', source_variant='primary')
        ft._journal(ev, journal_ntfs(10), 'C:', '', common,
                    source_snapshot='vss:{AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE}', source_variant='recovered')
        self.assertTrue(all(row['prov']['source_snapshot'] == 'vss:' + str(COPY_IDS[0]) for row in ev.rows))
        self.assertTrue(all(row['prov']['source_variant'] == 'recovered' for row in ev.rows))
        self.assertEqual(common['source_snapshot'], 'base-volume')
        self.assertEqual(common['source_variant'], 'primary')


if __name__ == '__main__':
    unittest.main()
