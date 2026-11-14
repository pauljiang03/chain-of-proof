"""USN creation/removal observations on synthetic records, without disk images."""
from types import SimpleNamespace as NS
import unittest

from extractor import filetraces as ft

BASE_FT = 130717152000000000        # 2015-03-25 00:00:00 UTC
BASE_US = 1427241600000000
ROOT = (5, 1)
COMMON = {'image': 'pc.E01', 'exhibit': 'PC', 'tool': 'test'}


def ref(value):
    segment, sequence = value
    return NS(SegmentNumberLowPart=segment & 0xFFFFFFFF,
              SegmentNumberHighPart=segment >> 32, SequenceNumber=sequence)


def record(usn, name, reason, own=(40, 2), parent=(10, 3), second=None):
    second = usn if second is None else second
    return NS(filename=name, record=NS(Usn=usn, TimeStamp=BASE_FT + second * 10_000_000,
                                      Reason=reason, FileReferenceNumber=ref(own),
                                      ParentFileReferenceNumber=ref(parent)))


class Mft:
    def __init__(self, paths):
        self.paths = {5: (1, '')}
        self.paths.update(paths)

    def __call__(self, segment):
        sequence, path = self.paths[segment]
        return NS(segment=segment, header=NS(SequenceNumber=sequence), full_path=lambda: path)

    def get(self, path):
        for segment, (_sequence, name) in self.paths.items():
            if name == path:
                return self(segment)
        raise KeyError(path)


class Collector:
    def __init__(self):
        self.rows, self.problems = [], []

    def add(self, kind, t, res, obj, aux='', **prov):
        self.rows.append(dict(kind=kind, t=t, res=res, obj=obj, aux=aux, prov=prov))

    def problem(self, source, error):
        self.problems.append((source, str(error)))


def collect(records, paths=None, identity=False, **kwargs):
    ntfs = NS(serial=0x12345678CA0C7A48, mft=Mft(paths or {10: (3, 'Users/informant/Temp')}),
              usnjrnl=NS(records=lambda: iter(records)))
    ev = Collector()
    first = ft._journal(ev, ntfs, 'C:', '', COMMON, **kwargs)
    if not identity:
        ev.rows = [r for r in ev.rows if r['kind'] not in ('journalName', 'journalParent', 'journalRemoval')]
    return first, ev


class JournalEvents(unittest.TestCase):
    def test_accumulated_create_and_close_flags_are_one_observation(self):
        first, ev = collect([
            record(10, 'x.txt', ft.USN_FILE_CREATE),
            record(20, 'x.txt', ft.USN_FILE_CREATE | 2),
            record(30, 'x.txt', ft.USN_FILE_CREATE | 2 | ft.USN_CLOSE),
            record(40, 'x.txt', ft.USN_FILE_DELETE | ft.USN_CLOSE),
        ])
        self.assertEqual(first, 10)
        self.assertEqual([r['kind'] for r in ev.rows], ['fileCreationRecorded', 'fileRemoved'])
        born, removed = ev.rows
        self.assertEqual(born['obj'], 'x.txt')
        self.assertEqual(born['prov']['context_path'], r'C:\Users\informant\Temp\x.txt')
        self.assertFalse(born['prov']['path_resolved'])
        self.assertEqual(born['aux'], 'CA0C7A48')
        self.assertEqual(born['t'], BASE_US + 10_000_000)
        self.assertEqual(born['prov']['matching_usns'], [10, 20, 30])
        self.assertEqual(born['prov']['close_usn'], 30)
        self.assertEqual(born['prov']['timestamp_semantics'], 'journal_observation')
        self.assertIn('not a file-system timestamp', born['prov']['time_meaning'])
        self.assertEqual(removed['t'], BASE_US + 40_000_000)
        self.assertEqual(removed['prov']['file_sequence'], 2)
        self.assertEqual(removed['prov']['parent_sequence'], 3)
        self.assertEqual(ev.problems, [])
        self.assertNotIn('fileDeleted', [r['kind'] for r in ev.rows])
        self.assertNotIn('fileCreated', [r['kind'] for r in ev.rows])

    def test_close_only_record_keeps_observation_time_without_backdating(self):
        _, ev = collect([record(50, 'x.txt', ft.USN_FILE_CREATE | ft.USN_CLOSE)])
        self.assertEqual(len(ev.rows), 1)
        self.assertEqual(ev.rows[0]['t'], BASE_US + 50_000_000)
        self.assertEqual(ev.rows[0]['prov']['reason_flags'], ft.USN_FILE_CREATE | ft.USN_CLOSE)

    def test_parent_paths_use_the_name_at_each_event_usn(self):
        parent = (10, 3)
        _, ev = collect([
            record(1, 'old', ft.USN_FILE_CREATE | ft.USN_CLOSE, own=parent, parent=ROOT),
            record(10, 'first.txt', ft.USN_FILE_CREATE | ft.USN_CLOSE, own=(40, 2)),
            record(20, 'old', ft.USN_RENAME_OLD, own=parent, parent=ROOT),
            record(21, 'new', ft.USN_RENAME_NEW | ft.USN_CLOSE, own=parent, parent=ROOT),
            record(30, 'last.txt', ft.USN_FILE_CREATE | ft.USN_CLOSE, own=(41, 2)),
        ], paths={10: (3, 'new')})
        files = {r['prov'].get('raw_name'): r for r in ev.rows}
        self.assertEqual(files['first.txt']['obj'], r'C:\old\first.txt')
        self.assertEqual(files['last.txt']['obj'], r'C:\new\last.txt')
        self.assertEqual(files['first.txt']['prov']['folder_names_from'], 'change journal')

    def test_reused_parent_record_and_missing_path_do_not_invent_a_parent(self):
        for paths in ({10: (4, 'unrelated')}, {10: (3, None)}, {99: (1, 'unrelated')}):
            with self.subTest(paths=paths):
                _, ev = collect([record(10, 'x.txt', ft.USN_FILE_DELETE | ft.USN_CLOSE)], paths=paths)
                row = ev.rows[0]
                self.assertEqual(row['obj'], 'x.txt')
                self.assertFalse(row['prov']['path_resolved'])
                self.assertEqual(row['prov']['parent_folder'], 'not resolved')
                self.assertEqual(row['prov']['parent_sequence'], 3)

    def test_file_reference_sequences_keep_reused_records_separate(self):
        _, ev = collect([
            record(10, 'old.txt', ft.USN_FILE_CREATE, own=(40, 2)),
            record(20, 'new.txt', ft.USN_FILE_CREATE | ft.USN_CLOSE, own=(40, 3)),
        ])
        self.assertEqual(len(ev.rows), 2)
        self.assertEqual([r['prov']['file_sequence'] for r in ev.rows], [2, 3])
        self.assertEqual([r['prov']['matching_usns'] for r in ev.rows], [[10], [20]])

    def test_snapshot_cutoff_avoids_overlap_with_live_journal(self):
        rows = [record(10, 'x.txt', ft.USN_FILE_CREATE | ft.USN_CLOSE),
                record(20, 'x.txt', ft.USN_FILE_DELETE | ft.USN_CLOSE)]
        _, ev = collect(rows, only_before=20, volume_serial='AABBCCDD', journal_source='snapshot')
        self.assertEqual(len(ev.rows), 1)
        self.assertEqual(ev.rows[0]['prov']['usn'], 10)
        self.assertEqual(ev.rows[0]['aux'], 'AABBCCDD')
        self.assertEqual(ev.rows[0]['prov']['journal_source'], 'snapshot')

    def test_future_parent_record_does_not_supply_a_historical_path(self):
        _, ev = collect([
            record(10, 'child.txt', ft.USN_FILE_CREATE | ft.USN_CLOSE),
            record(20, 'future', ft.USN_FILE_CREATE | ft.USN_CLOSE, own=(10, 3), parent=ROOT),
        ], paths={10: (4, 'later-reuse')})
        row = ev.rows[0]
        self.assertEqual(row['obj'], 'child.txt')
        self.assertFalse(row['prov']['path_resolved'])

    def test_raw_filename_is_preserved_even_with_slash_characters(self):
        name = 'S9(wQm9ff_gd/hZ~c'
        _, ev = collect([record(10, name, ft.USN_FILE_DELETE | ft.USN_CLOSE)])
        self.assertEqual(ev.rows[0]['prov']['raw_name'], name)
        self.assertEqual(ev.rows[0]['obj'], name)
        self.assertTrue(ev.rows[0]['prov']['context_path'].endswith('\\' + name))

    def test_unreadable_name_on_close_still_ends_accumulation(self):
        class Unreadable:
            record = record(20, 'x', ft.USN_CLOSE).record

            @property
            def filename(self):
                raise ValueError('damaged name')

        _, ev = collect([record(10, 'x.txt', ft.USN_FILE_CREATE), Unreadable(),
                         record(30, 'x.txt', ft.USN_FILE_CREATE | ft.USN_CLOSE)])
        self.assertEqual(len(ev.rows), 2)
        self.assertEqual([r['prov']['close_usn'] for r in ev.rows], [20, 30])
        self.assertEqual(len(ev.problems), 1)


if __name__ == '__main__':
    unittest.main()
