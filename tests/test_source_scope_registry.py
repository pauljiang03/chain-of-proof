"""Synthetic registry/source scope regressions; no image or answer key required."""
from datetime import datetime, timezone
import json
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from extractor import application_identity, hacking, host_attributes, system
from extractor.source_scope import base_volume_scope
from extractor.store import Evidence


EXAMINED = 1800000000000000
STAMP = datetime(2015, 3, 25, tzinfo=timezone.utc)
VSS = 'vss:00000000-0000-0000-0000-000000000001'


def common(**specific):
    return dict(base_volume_scope(), image='synthetic.E01', exhibit='OTHER-PC', **specific)


def hive(name='SYSTEM', path=r'C:\Windows\System32\config\SYSTEM', backup=False):
    return system.Hive(name, None, path, backup, None, None)


def records(ev, kind=None):
    return [(row, json.loads(row[-1])) for row in ev.rows() if kind is None or row[0] == kind]


def value(name, data):
    return SimpleNamespace(name=name, value=data)


class RegistryScope(unittest.TestCase):
    def test_backup_is_a_variant_on_its_actual_snapshot(self):
        backup = hive(path=r'C:\Windows\System32\config\RegBack\SYSTEM')
        where = system._where(backup)
        self.assertEqual(where['source_variant'], 'registry-backup:' + backup.path)
        self.assertNotIn('source_snapshot', where)
        self.assertEqual(system._where(hive())['source_variant'], 'primary')
        for missing in ('  ', None):
            self.assertEqual(system._where(hive(path=missing))['source_variant'], 'unknown')

    def test_control_set_selection_and_backup_axes_do_not_imply_currentness(self):
        live = hive()
        self.assertEqual(system._where(live, 'ControlSet001', 'ControlSet001')['source_variant'], 'primary')
        self.assertEqual(system._where(live, 'ControlSet002', 'ControlSet001')['source_variant'],
                         'noncurrent-control-set:ControlSet002')
        self.assertEqual(system._where(live, 'ControlSet001', None)['source_variant'], 'unknown')
        backup = hive(path=r'C:\Windows\System32\config\RegBack\SYSTEM', backup=True)
        where = system._where(backup, 'ControlSet002', 'ControlSet001')
        self.assertEqual(where['source_variant'], 'registry-backup:' + backup.path)
        self.assertEqual(where['control_set'], 'ControlSet002')
        self.assertEqual(where['current_control_set'], 'ControlSet001')

    def test_common_scope_cannot_override_specific_origin_or_deduplicate_it(self):
        ev = Evidence()
        out = system._Out(ev, common(), EXAMINED)
        path = r'C:\Windows\System32\config\RegBack\SYSTEM'
        for detail in ({}, {'source_variant': 'registry-backup:' + path},
                       {'source_variant': 'noncurrent-control-set:ControlSet002'},
                       {'source_snapshot': VSS}, {'source_snapshot': VSS}):
            out.add('sessionEvent', 1, 1, 'shutdown', '', _copy=True, artifact='same record', **detail)
        rows = records(ev)
        self.assertEqual(len(rows), 4)
        self.assertEqual({(p['source_snapshot'], p['source_variant']) for _, p in rows},
                         {('base-volume', 'primary'), ('base-volume', 'registry-backup:' + path),
                          ('base-volume', 'noncurrent-control-set:ControlSet002'), (VSS, 'primary')})

    def test_explicit_unknown_does_not_fall_back_to_primary(self):
        ev = Evidence()
        system._Out(ev, common()).add('systemSetting', 1, 1, 'x', 'y', source_variant=None)
        self.assertEqual(records(ev)[0][1]['source_variant'], 'unknown')
        ev = Evidence()
        system._Out(ev, {'image': 'synthetic.E01'}).add('systemSetting', 1, 1, 'x', 'y')
        self.assertEqual(records(ev)[0][1]['source_snapshot'], 'unknown')
        self.assertEqual(records(ev)[0][1]['source_variant'], 'unknown')

    def test_execution_subject_binds_specific_snapshot_and_registry_variant(self):
        ev = Evidence()
        out = system._Out(ev, common(), EXAMINED)
        backup = 'registry-backup:C:\\Windows\\System32\\config\\RegBack\\SYSTEM'
        for detail in ({}, {'source_variant': backup}, {'source_snapshot': VSS}):
            system._execution_attributes(out, 'different.exe', r'D:\Tools\different.exe', 1,
                                         'synthetic reviewed entry', 'same artifact', {'entry': 7}, **detail)
        subjects = records(ev, 'attributeSubject')
        self.assertEqual(len({row[4] for row, _ in subjects}), 3)
        for row, provenance in subjects:
            scope = json.loads(row[4])
            self.assertEqual(scope[2:4], [provenance['source_snapshot'], provenance['source_variant']])
        self.assertTrue(all(row[1] == EXAMINED for row, _ in subjects))

    def test_shutdown_reader_keeps_equal_times_in_distinct_control_sets(self):
        ev = Evidence()
        raw = struct.pack('<Q', 130717152000000000)
        key = SimpleNamespace(values=lambda: [value('ShutdownTime', raw)])
        with patch.object(system, '_control_sets', return_value=('ControlSet001', ['ControlSet001', 'ControlSet002'])), \
                patch.object(system, '_open', return_value=key):
            system._registry_sessions(system._Out(ev, common()), ev, [hive()])
        rows = records(ev, 'sessionEvent')
        self.assertEqual(len(rows), 2)
        self.assertEqual({p['source_variant'] for _, p in rows}, {'primary', 'noncurrent-control-set:ControlSet002'})

    def test_fallback_system_settings_are_unknown_not_primary(self):
        ev = Evidence()
        key = SimpleNamespace(timestamp=STAMP, values=lambda: [value('ComputerName', 'OTHER-HOST')])
        with patch.object(system, '_control_sets', return_value=(None, ['ControlSet001'])), \
                patch.object(system, '_open', side_effect=lambda ev, h, path: key if path.endswith('ComputerName\\ComputerName') else None), \
                patch.object(system, '_network'), patch.object(system, '_partitions'):
            system._settings(system._Out(ev, common()), ev, None, [hive()], None, {})
        rows = records(ev, 'systemSetting')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1]['source_variant'], 'unknown')
        self.assertEqual(rows[0][1]['control_set'], 'ControlSet001')

    def test_invalid_or_dangling_select_current_is_unknown(self):
        for current in (True, 0, -1, 9999, '1', 3):
            with self.subTest(current=current):
                key = SimpleNamespace(values=lambda: [value('Current', current)])
                current_hive = hive()._replace(hive=SimpleNamespace(root=lambda: None))
                with patch.object(system, '_open', return_value=key), \
                        patch.object(system, '_subkeys', return_value=[SimpleNamespace(name='ControlSet001')]):
                    self.assertEqual(system._control_sets(None, current_hive), (None, ['ControlSet001']))

    def test_legacy_mail_config_preserves_backup_and_vss_scope(self):
        account = SimpleNamespace(path=r'Software\Microsoft\Internet Account Manager\Accounts\Other',
                                  values=lambda: [value('SMTP Email Address', 'unrelated@example.test')])
        node = SimpleNamespace(key=lambda path: SimpleNamespace(subkeys=lambda: [account]))
        primary = system.Hive('S-1-OTHER', node, r'C:\Users\Other\NTUSER.DAT', False, 'Other', 'S-1-OTHER')
        backup = primary._replace(path=r'C:\RegBack\NTUSER.DAT', backup=True)
        target = SimpleNamespace(registry=SimpleNamespace(load_user_hives=lambda: None))
        ev = Evidence()
        with patch.object(system, '_hives', return_value=[primary, backup]):
            for snapshot in ('base-volume', VSS):
                hacking._mail_accounts(ev, target, {'common': dict(common(), source_snapshot=snapshot),
                                                   'examined_at': EXAMINED})
        rows = records(ev, 'attributeSubject')
        self.assertEqual(len(rows), 4)
        self.assertEqual(len({row[4] for row, _ in rows}), 4)
        self.assertEqual({(p['source_snapshot'], p['source_variant']) for _, p in rows},
                         {(snapshot, variant) for snapshot in ('base-volume', VSS)
                          for variant in ('primary', 'registry-backup:' + backup.path)})

    def test_host_current_metadata_skips_regback_and_scopes_subject(self):
        primary = hive(name='SOFTWARE', path=r'C:\Windows\System32\config\SOFTWARE')
        # The path independently detects backup even if the flag is missing.
        backup = primary._replace(path=r'C:\Windows\System32\config\RegBack\SOFTWARE')
        ev = Evidence()
        visited = []
        key = SimpleNamespace(values=lambda: [value('ProductName', 'Other OS')])
        def open_key(ev, h, path):
            visited.append(h.path)
            return key if path == r'Microsoft\Windows NT\CurrentVersion' else None
        with patch.object(system, '_hives', return_value=[primary, backup]), patch.object(system, '_open', side_effect=open_key):
            for snapshot in ('base-volume', VSS):
                host_attributes.extract(ev, None, {'common': dict(common(), source_snapshot=snapshot),
                                                   'examined_at': EXAMINED})
        rows = records(ev, 'attributeSubject')
        self.assertEqual(len(rows), 2)
        self.assertEqual(len({row[4] for row, _ in rows}), 2)
        self.assertNotIn(backup.path, visited)

    def test_registered_binary_metadata_subjects_do_not_cross_snapshots(self):
        from tests.test_application_identity import pe
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic.exe'
            path.write_bytes(pe())
            target = SimpleNamespace(fs=SimpleNamespace(path=lambda source: path))
            ev = Evidence()
            with patch.object(application_identity, '_registered', return_value=[(r'D:\Other\literal.exe', {})]):
                for snapshot in ('base-volume', VSS):
                    application_identity.extract(ev, target, {'common': dict(common(), source_snapshot=snapshot),
                                                              'examined_at': EXAMINED})
            self.assertEqual(ev.problems, [])
            rows = records(ev, 'attributeSubject')
            self.assertTrue(rows)
            by_snapshot = {snapshot: {row[4] for row, p in rows if p['source_snapshot'] == snapshot}
                           for snapshot in ('base-volume', VSS)}
            self.assertTrue(by_snapshot['base-volume'].isdisjoint(by_snapshot[VSS]))

    def test_registered_binary_inventory_cannot_use_a_regback_registration(self):
        backup = hive(name='SOFTWARE', path=r'C:\Windows\System32\config\RegBack\SOFTWARE')
        with patch.object(system, '_hives', return_value=[backup]), patch.object(system, '_open') as opened:
            self.assertEqual(list(application_identity._registered(Evidence(), None)), [])
            opened.assert_not_called()


if __name__ == '__main__':
    unittest.main()
