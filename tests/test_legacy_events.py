"""Synthetic EVT binary fixtures, with genuine dissect decoding when installed."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from extractor import legacy_events
from extractor.store import Evidence
from extractor.system import _Out


def evt(records):
    items = []
    for number, provider, code, seconds in records:
        names = (provider + '\0TEST-PC\0').encode('utf-16-le')
        padding = b'\0' * ((-len(names)) % 4)
        length = 56 + len(names) + len(padding) + 4
        header = struct.pack('<6I4H6I', length, 0x654c664c, number, seconds,
                             seconds + 7, code, 4, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        items.append(header + names + padding + struct.pack('<I', length))
    size = 48 + sum(map(len, items))
    header = struct.pack('<I4s10I', 48, b'LfLe', 1, 1, 48, size,
                         len(records) + 1, 1, size, 0, 0, 48)
    return header + b''.join(items)


def target_for(root):
    def resolve(path):
        if path != '%windir%/system32/config':
            raise AssertionError(path)
        return root / 'WINNT' / 'system32' / 'config'
    return SimpleNamespace(resolve=resolve)


class PureLegacyEvents(unittest.TestCase):
    def test_only_exact_source_and_supported_codes_are_interpreted(self):
        ev = Evidence()
        out = _Out(ev, {'image': 'synthetic.E01', 'exhibit': 'TEST'})
        common = dict(TimeGenerated=datetime(2024, 1, 2, tzinfo=timezone.utc),
                      TimeWritten=datetime(2024, 1, 2, tzinfo=timezone.utc),
                      RecordNumber=9, EventID=6005, Computername='OTHER-PC')
        for provider, code in [('Security', 528), ('Security', 540), ('Other', 6005), ('EventLog', 6008)]:
            self.assertFalse(legacy_events._event(out, SimpleNamespace(**common, SourceName=provider, EventCode=code), 'x.evt'))
        self.assertEqual(ev.rows(), [])
        bad = dict(common, TimeGenerated=datetime(2024, 1, 2))
        with self.assertRaisesRegex(ValueError, 'timezone'):
            legacy_events._event(out, SimpleNamespace(**bad, SourceName='EventLog', EventCode=6005), 'x.evt')


try:
    HAS_EVT = importlib.util.find_spec('dissect.eventlog.evt') is not None
except ModuleNotFoundError:
    HAS_EVT = False


@unittest.skipUnless(HAS_EVT, 'optional dissect.eventlog package is not installed')
class LegacyEventFiles(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.directory = self.root / 'WINNT' / 'system32' / 'config'
        self.directory.mkdir(parents=True)
        self.ev = Evidence()
        self.out = _Out(self.ev, {'image': 'synthetic.E01', 'exhibit': 'TEST'})
        self.target = target_for(self.root)

    def test_genuine_evt_uses_generated_time_low_event_code_and_record_number(self):
        (self.directory / 'SysEvent.EvT').write_bytes(evt([
            (11, 'EventLog', 0x80000000 | 6005, 1700000000),
            (12, 'EventLog', 6006, 1700000300),
            (13, 'Security', 528, 1700000400),
            (14, 'Security', 540, 1700000500)]))
        result = legacy_events.extract_sessions(self.out, self.ev, self.target)
        self.assertEqual(result['records_examined'], 4)
        self.assertEqual(result['events_emitted'], 2)
        self.assertEqual(result['unsupported_records'], 2)
        self.assertEqual(self.ev.problems, [])
        rows = self.ev.rows()
        self.assertEqual([(row[1], row[2], row[3]) for row in rows],
                         [(1700000000000000, 1000000, 'startup'), (1700000300000000, 1000000, 'shutdown')])
        provenance = json.loads(rows[0][-1])
        self.assertTrue(provenance['source_path'].endswith('WINNT\\system32\\config\\SysEvent.EvT'))
        self.assertEqual(provenance['record_number'], 11)
        self.assertEqual(provenance['raw_event_id'], 0x80000000 | 6005)
        self.assertIn('record 11', provenance['artifact'])
        self.assertIn('service was started', provenance['event'])
        self.assertIn('exact machine power', provenance['limitation'])
        self.assertNotEqual(provenance['time_generated'], provenance['time_written'])

    def test_parse_failure_does_not_discard_independent_good_file(self):
        (self.directory / 'Bad.evt').write_bytes(b'not an event log')
        (self.directory / 'Good.evt').write_bytes(evt([(1, 'EventLog', 6006, 1700000000)]))
        result = legacy_events.extract_sessions(self.out, self.ev, self.target)
        self.assertEqual(result['events_emitted'], 1)
        self.assertEqual(result['failed_files'], 1)
        self.assertEqual(len(self.ev.problems), 1)
        self.assertIn('Bad.evt', self.ev.problems[0])

    def test_limits_are_explicit_and_not_a_clean_zero_result(self):
        (self.directory / 'System.evt').write_bytes(evt([(1, 'EventLog', 6005, 1700000000)]))
        with patch.object(legacy_events, 'MAX_RECORDS', 0):
            result = legacy_events.extract_sessions(self.out, self.ev, self.target)
        self.assertEqual(result['failed_files'], 1)
        self.assertEqual(result['events_emitted'], 0)
        self.assertIn('limit', self.ev.problems[0])
        self.ev.problems.clear()
        with patch.object(legacy_events, 'MAX_LOG_BYTES', 1):
            result = legacy_events.extract_sessions(self.out, self.ev, self.target)
        self.assertEqual(result['failed_files'], 1)
        self.assertIn('limit', self.ev.problems[0])

    def test_missing_logs_are_reported_and_never_replaced_by_observation_time(self):
        result = legacy_events.extract_sessions(self.out, self.ev, self.target)
        self.assertEqual(result['failed_files'], 1)
        self.assertEqual(self.ev.rows(), [])
        self.assertIn('no legacy .evt files', self.ev.problems[0])


if __name__ == '__main__':
    unittest.main()
