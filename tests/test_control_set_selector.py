"""Currentness must follow one native DWORD selector, never a decoded lookalike."""
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from extractor import system, structured_system
from extractor.store import Evidence


class ControlSetSelector(unittest.TestCase):
    def run_selector(self, values, names=('ControlSet001', 'ControlSet002')):
        root = NS(subkeys=lambda: [NS(name=name) for name in names])
        hive = system.Hive('SYSTEM', NS(root=lambda: root), r'C:\Windows\System32\config\SYSTEM',
                           False, None, None)
        selected = NS(path='Select', values=lambda: iter(values))
        evidence = Evidence()
        with patch.object(system, '_open', return_value=selected):
            result = system._control_sets(evidence, hive)
        return result, evidence

    def test_native_dword_selects_existing_set_case_insensitively(self):
        for name in ('Current', 'current', 'CURRENT'):
            result, evidence = self.run_selector([NS(name=name, value=2, type=4)])
            self.assertEqual(result, ('ControlSet002', ['ControlSet002', 'ControlSet001']))
            self.assertEqual(evidence.problems, [])

    def test_wrong_registry_types_never_select(self):
        for kind in (0, 1, 2, 3, 5, 7, 11, None, '4'):
            with self.subTest(kind=kind):
                result, evidence = self.run_selector([NS(name='Current', value=2, type=kind)])
                self.assertIsNone(result[0])
                self.assertTrue(evidence.problems)

    def test_missing_duplicate_undecodable_and_invalid_values_never_select(self):
        cases = [[], [NS(name='Current', value=2)],
                 [NS(name='Current', value=2, type=4), NS(name='CURRENT', value=1, type=4)]]
        cases += [[NS(name='Current', value=value, type=4)]
                  for value in (True, False, '2', 2.0, 0, -1, 1000, None)]
        for values in cases:
            with self.subTest(values=values):
                result, evidence = self.run_selector(values)
                self.assertIsNone(result[0])
                self.assertTrue(evidence.problems)

    def test_dangling_dword_is_not_a_fallback_primary_set(self):
        result, _ = self.run_selector([NS(name='Current', value=3, type=4)])
        self.assertIsNone(result[0])
        self.assertEqual(result[1], ['ControlSet001', 'ControlSet002'])

    def test_wrong_type_prevents_native_search_service_extraction(self):
        for kind in (5, 11):
            evidence = Evidence()
            root = NS(subkeys=lambda: [NS(name='ControlSet002')])
            hive = system.Hive('SYSTEM', NS(root=lambda: root), r'C:\Windows\System32\config\SYSTEM',
                               False, None, None)
            opened = []
            def open_key(ev, h, path):
                opened.append(path)
                if path == 'Select':
                    return NS(path=path, values=lambda: [NS(name='Current', value=2, type=kind)])
                return NS(path=path, values=lambda: [NS(name='Start', value=2, type=4)])
            with patch.object(system, '_hives', return_value=[hive]), \
                    patch.object(system, '_open', side_effect=open_key):
                structured_system.registry(evidence, None, {'examined_at': 100, 'common': {
                    'image': 'pc.E01', 'exhibit': 'PC', 'source_snapshot': 'base-volume',
                    'source_variant': 'primary'}})
            self.assertEqual(opened, ['Select'])
            self.assertFalse(list(evidence.rows()))
            self.assertTrue(evidence.problems)


if __name__ == '__main__':
    unittest.main()
