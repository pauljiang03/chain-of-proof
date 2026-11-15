"""Configuration preservation tests; no disk image required."""
import json
from datetime import datetime, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from extractor import system as s


class Sink:
    def __init__(self):
        self.rows = []
    def add(self, *args, **kwargs):
        self.rows.append((args, kwargs))


def test_registry_configuration_preserves_zero_and_multi_string():
    out = Sink()
    h = s.Hive('SYSTEM', None, 'C:\\Windows\\System32\\config\\SYSTEM', False, None, None)
    key = SimpleNamespace(timestamp=datetime(2015, 3, 22, tzinfo=timezone.utc))
    values = {'Start': 0, 'OutlookOST': ['$UserProfile$\\mail\\*.ost'], 'DataDirectory': '%ProgramData%\\Microsoft\\Search\\Data\\', 'Binary': b'bytes'}
    with patch.object(s, '_open', return_value=key), patch.object(s, '_vals', return_value=values):
        s._registry_settings(out, None, h, 'ControlSet001\\Config', tuple(values), 'registry key last-write time')
    assert [r[1]['registry_value'] for r in out.rows] == [0, ['$UserProfile$\\mail\\*.ost'], '%ProgramData%\\Microsoft\\Search\\Data\\']
    assert out.rows[0][1]['artifact'].endswith('value Start')
    assert out.rows[1][1]['time_meaning'] == 'registry key last-write time'
    assert out.rows[0][0][3:] == ('HKLM\\SYSTEM\\ControlSet001\\Config value Start', '0')
    assert json.loads(out.rows[1][0][4]) == values['OutlookOST']
    assert out.rows[2][0][4] == values['DataDirectory']
    assert out.rows[0][0][1] == s.us(key.timestamp)
    assert out.rows[0][1]['registry_path'] == 'HKLM\\SYSTEM\\ControlSet001\\Config'
    assert out.rows[0][1]['registry_value_name'] == 'Start'
    assert out.rows[0][1]['hive'] == h.path


def test_settings_exports_system_root_from_value_without_assuming_path():
    out = Sink()
    h = s.Hive('SOFTWARE', None, 'software', False, None, None)
    key = SimpleNamespace(timestamp=datetime(2015, 3, 22, tzinfo=timezone.utc))
    with patch.object(s, '_open', return_value=key), patch.object(s, '_vals', return_value={'SystemRoot': 'D:\\Windows'}), patch.object(s, '_partitions'):
        s._settings(out, None, None, [h], None, {})
    row = next(r for r in out.rows if r[0][3] == 'system root')
    assert row[0][4] == 'D:\\Windows'
    assert row[1]['artifact'].endswith('CurrentVersion value SystemRoot')


def test_missing_registry_key_emits_nothing():
    out = Sink()
    with patch.object(s, '_open', return_value=None):
        s._registry_settings(out, None, None, 'missing', ('Start',), 'registry key last-write time')
    assert out.rows == []


def test_selected_control_set_and_zone_are_used_verbatim():
    out = Sink()
    system = s.Hive('SYSTEM', None, 'system', False, None, None)
    software = s.Hive('SOFTWARE', None, 'software', False, None, None)
    key = SimpleNamespace(timestamp=datetime(2015, 3, 22, tzinfo=timezone.utc))
    opened = []
    def open_key(ev, hive, path):
        opened.append(path)
        return key if path.endswith('TimeZoneInformation') else None
    with patch.object(s, '_open', side_effect=open_key), patch.object(s, '_vals', return_value={'TimeZoneKeyName': 'Pacific Standard Time', 'Bias': 480}), patch.object(s, '_network'):
        s._system_hive_settings(out, None, None, [system, software], system, 'ControlSet002', 'America/Los_Angeles', 'registry key last-write time')
    assert 'ControlSet002\\Services\\WSearch' in opened
    assert 'Microsoft\\Windows NT\\CurrentVersion\\Time Zones\\Pacific Standard Time' in opened
    assert out.rows[0][0][4] == 'Pacific Standard Time'


class ConfigurationGaps(unittest.TestCase):
    def test_registry_configuration(self):
        test_registry_configuration_preserves_zero_and_multi_string()

    def test_system_root(self):
        test_settings_exports_system_root_from_value_without_assuming_path()

    def test_missing_key(self):
        test_missing_registry_key_emits_nothing()

    def test_selected_scope(self):
        test_selected_control_set_and_zone_are_used_verbatim()


if __name__ == '__main__':
    unittest.main()
