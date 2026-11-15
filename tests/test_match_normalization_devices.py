"""Device names and extended-path syntax never collapse namespace identities."""
from copy import deepcopy
import unittest

from eval.match_normalization import normalize
from tests.test_match_normalization import profile, path_rule


class MatchNormalizationDevices(unittest.TestCase):
    def test_reserved_names_extensions_case_and_spaces_refuse_in_all_components(self):
        names = ['CON', 'PRN', 'AUX', 'NUL', 'CONIN$', 'CONOUT$']
        names += [prefix + digit for prefix in ('COM', 'LPT') for digit in '123456789¹²³']
        for name in names:
            for variant in (name, name.lower(), name + '.txt', name.lower() + '.tar.gz',
                            name + ' .txt', ' ' + name + '.txt'):
                for prefix in ('C:\\', 'C:\\Folder\\', '\\\\?\\C:\\', '\\Folder\\'):
                    for case_sensitive in (True, False):
                        with self.subTest(name=variant, prefix=prefix, sensitive=case_sensitive), self.assertRaises(ValueError):
                            normalize(prefix + variant, path_rule(case_sensitive=case_sensitive), profile=profile())
        for name in ('NUL', 'CON.txt', 'COM¹'):
            with self.assertRaisesRegex(ValueError, 'reserved_windows_device_component'):
                normalize('C:\\' + name + '\\ordinary.bin', path_rule(), profile=profile())

    def test_unc_and_extended_unc_device_components_refuse(self):
        public = profile()
        public['source_contexts']['volume']['absolute_roots'] = [r'\\server\share']
        for prefix in ('\\\\server\\share\\', '\\\\?\\UNC\\server\\share\\'):
            for name in ('NUL', 'cOn.txt', 'COM¹', 'Lpt².tar.gz', 'AUX .txt', 'CONOUT$'):
                with self.subTest(prefix=prefix, name=name), self.assertRaisesRegex(ValueError, 'reserved_windows_device_component'):
                    normalize(prefix + name, path_rule(), profile=public)

    def test_four_review_counterexamples_refuse_instead_of_matching(self):
        for ordinary, extended in [(r'C:\NUL', r'\\?\C:\NUL'),
                                   (r'C:\CON.txt', r'\\?\C:\CON.txt'),
                                   ('C:\\COM¹', '\\\\?\\C:\\COM¹')]:
            for value in (ordinary, extended):
                with self.assertRaises(ValueError): normalize(value, path_rule(), profile=profile())
        with self.assertRaisesRegex(ValueError, 'invalid_extended_windows_path_representation'):
            normalize(r'\\?\C:/Folder/file', path_rule(), profile=profile())

    def test_extended_slash_spellings_refuse_before_separator_conversion(self):
        public = profile()
        public['source_contexts']['volume']['absolute_roots'].append(r'\\server\share')
        for value in [r'\\?\C:/Folder/file', r'\\?\C:\Folder/file', '//?/C:/Folder/file',
                      r'\\?\UNC\server\share\Folder/file', '//?/UNC/server/share/Folder/file']:
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'invalid_extended_windows_path_representation'):
                normalize(value, path_rule(), profile=public)

    def test_ordinary_nondevice_names_and_documented_extended_paths_still_work(self):
        rule, public = path_rule(), profile()
        before = deepcopy(public)
        for name in ('CONSOLE.txt', 'NULx', 'auxiliary', 'COM10', 'LPT10', 'COM⁴', '.CON', 'foo.CON'):
            ordinary = 'C:\\Folder\\' + name
            self.assertEqual(normalize(ordinary, rule, profile=public),
                             normalize('\\\\?\\' + ordinary, rule, profile=public))
        self.assertEqual(normalize('C:/Folder/file', rule, profile=public),
                         normalize(r'C:\Folder\file', rule, profile=public))
        self.assertEqual(public, before)
