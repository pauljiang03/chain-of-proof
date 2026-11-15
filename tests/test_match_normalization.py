"""Synthetic opt-in representation equivalence; no reference or evidence values."""
from copy import deepcopy
import unittest

from eval.match_normalization import normalize, validate_config, validate_profile, validate_rule


def profile():
    return {'id': 'typed-representation-v1', 'version': 1, 'ancestor_public_sha256': 'a' * 64,
            'source_contexts': {'volume': {'origin': {'image': 'fixture.E01', 'exhibit': 'SYNTHETIC',
                'source_snapshot': 'base-volume', 'source_variant': 'primary'},
                'volume': {'kind': 'ntfs-serial-64', 'value': '0123456789abcdef'},
                'absolute_roots': ['C:'], 'mapping_receipt_sha256': 'b' * 64}}}


def path_rule(**extra):
    return dict({'kind': 'windows-volume-path-v1', 'context': 'volume',
                 'case_sensitive': True, 'allow_volume_rooted': True}, **extra)


class MatchNormalization(unittest.TestCase):
    def test_guid_surface_forms_are_symmetric_and_preserve_all_identity_bits(self):
        rule = {'kind': 'guid-v1'}
        spellings = ['01234567-89ab-cdef-0123-456789abcdef',
                     '{01234567-89AB-CDEF-0123-456789ABCDEF}', '0123456789abcdef0123456789abcdef']
        for left in spellings:
            for right in spellings:
                self.assertEqual(normalize(left, rule), normalize(right, rule))
        self.assertNotEqual(normalize(spellings[0], rule), normalize('01234567-89ab-cdef-0123-456789abcdee', rule))
        self.assertNotEqual(normalize(spellings[0], rule), normalize('67452301-ab89-efcd-0123-456789abcdef', rule))
        self.assertEqual(normalize('0' * 32, rule)[1], b'\0' * 16)

    def test_guid_malformed_and_non_ascii_inputs_refuse(self):
        for value in [' 0123456789abcdef0123456789abcdef', '{' + '0' * 32, '{{' + '0' * 32 + '}}',
                      'urn:uuid:' + '0' * 32, '0' * 31, '0' * 33, '０' * 32, '0' * 32 + '\0', None, 0]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize(value, {'kind': 'guid-v1'})

    def test_zone_fixed_grammar_preserves_label_and_numeric_offset(self):
        rule = {'kind': 'zone-label-offset-v1'}
        spellings = ['Fixture Standard Name (UTC+05:30)', 'Fixture Standard Name GMT+5:30',
                     '(UTC +05:30) Fixture Standard Name']
        for left in spellings:
            for right in spellings:
                self.assertEqual(normalize(left, rule), normalize(right, rule))
        for other in ['Fixture Daylight Name (UTC+05:30)', 'fixture standard name (UTC+05:30)',
                      'Fixture  Standard Name (UTC+05:30)', 'Fixture Standard Name (UTC-05:30)',
                      'Fixture Standard Name (UTC+05:00)']:
            self.assertNotEqual(normalize(spellings[0], rule), normalize(other, rule))
        self.assertEqual(normalize('Fixture (UTC+14:00)', rule)[2], 840)
        self.assertEqual(normalize('Fixture (UTC+00:00)', rule)[2], 0)

    def test_zone_signed_compact_and_bare_colon_are_exact_public_grammar(self):
        rule = {'kind': 'zone-label-offset-v1'}
        spellings = ['Synthetic Zone (UTC+02:30)', 'Synthetic Zone (+0230)',
                     'Synthetic Zone (+02:30)', 'Synthetic Zone +0230',
                     '(+02:30) Synthetic Zone']
        for left in spellings:
            for right in spellings:
                self.assertEqual(normalize(left, rule), normalize(right, rule))
        for value in ['Synthetic Zone (-0230)', 'Synthetic Zone (+0200)',
                      'Different Zone (+0230)', 'synthetic zone (+0230)']:
            self.assertNotEqual(normalize(spellings[0], rule), normalize(value, rule))
        self.assertEqual(normalize('Synthetic Zone (-0230)', rule), normalize('Synthetic Zone (UTC-02:30)', rule))
        for invalid in ['Synthetic Zone (+1430)', 'Synthetic Zone (+1460)', 'Synthetic Zone (+2400)',
                        'Synthetic Zone (-0000)', 'Synthetic Zone (-00:00)', 'Synthetic Zone (+230)',
                        'Synthetic Zone (+2:30)', 'Synthetic Zone (0230)', 'Synthetic Zone (＋0230)',
                        'Synthetic Zone (+02:30) -0230']:
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                normalize(invalid, rule)

    def test_zone_label_casefold_requires_its_own_explicit_option(self):
        left, right = 'Fixture Name (UTC+01:00)', 'fixture name (GMT+1:00)'
        self.assertNotEqual(normalize(left, {'kind': 'zone-label-offset-v1'}), normalize(right, {'kind': 'zone-label-offset-v1'}))
        self.assertEqual(normalize(left, {'kind': 'zone-label-offset-v1', 'label_mode': 'casefold'}),
                         normalize(right, {'kind': 'zone-label-offset-v1', 'label_mode': 'casefold'}))

    def test_zone_ambiguity_unknown_offset_and_dst_guesses_refuse(self):
        for value in ['UTC+01:00', 'Fixture (UTC-00:00)', 'Fixture (UTC+14:01)', 'Fixture (UTC+15:00)',
                      'Fixture (UTC+01:60)', 'Fixture (UTC+1)', 'Fixture (UTC+0100)', 'Fixture (UTC−01:00)',
                      'Fixture (UTC+０1:00)', 'Fixture (Z)', 'Fixture EST', 'Fixture (UTC+01:00) UTC+02:00',
                      ' Fixture (UTC+01:00)', 'Fixture (UTC+01:00) ', 'Fixture (UTC+01:00:00)']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize(value, {'kind': 'zone-label-offset-v1'})

    def test_path_rooted_equivalence_requires_reviewed_context(self):
        public = profile(); rule = path_rule()
        spellings = [r'C:\Folder\file.bin', r'\Folder\file.bin', 'C:/Folder/file.bin', r'\\?\C:\Folder\file.bin']
        for left in spellings:
            for right in spellings:
                self.assertEqual(normalize(left, rule, profile=public), normalize(right, rule, profile=public))
        self.assertNotEqual(normalize(spellings[0], rule, profile=public),
                            normalize(r'C:\folder\file.bin', rule, profile=public))
        folded = path_rule(case_sensitive=False)
        self.assertEqual(normalize(spellings[0], folded, profile=public),
                         normalize(r'C:\folder\file.bin', folded, profile=public))
        with self.assertRaises(ValueError): normalize(r'\Folder\file.bin', path_rule(allow_volume_rooted=False), profile=public)

    def test_other_drive_or_share_is_never_stripped(self):
        for value in [r'D:\Folder\file.bin', r'\\server\share\Folder\file.bin']:
            with self.assertRaises(ValueError): normalize(value, path_rule(), profile=profile())
        public = profile(); public['source_contexts']['volume']['absolute_roots'].append('D:')
        self.assertEqual(normalize(r'C:\Folder\file.bin', path_rule(), profile=public),
                         normalize(r'D:\Folder\file.bin', path_rule(), profile=public))
        public['source_contexts']['volume']['absolute_roots'] = [r'\\server\share']
        self.assertEqual(normalize(r'\\server\share\Folder\file.bin', path_rule(), profile=public),
                         normalize(r'\\?\UNC\server\share\Folder\file.bin', path_rule(), profile=public))
        with self.assertRaises(ValueError): normalize(r'\\server\other\Folder\file.bin', path_rule(), profile=public)

    def test_unc_roots_do_not_gain_unicode_aliases(self):
        public = profile()
        public['source_contexts']['volume']['absolute_roots'] = [r'\\server\straße']
        normalize(r'\\server\straße\file', path_rule(), profile=public)
        with self.assertRaises(ValueError):
            normalize(r'\\server\strasse\file', path_rule(), profile=public)

    def test_insensitive_path_components_fold_ascii_only(self):
        rule = path_rule(case_sensitive=False)
        self.assertEqual(normalize(r'C:\FOLDER\File', rule, profile=profile()),
                         normalize(r'C:\folder\file', rule, profile=profile()))
        self.assertNotEqual(normalize(r'C:\straße\file', rule, profile=profile()),
                            normalize(r'C:\strasse\file', rule, profile=profile()))
        self.assertNotEqual(normalize(r'C:\Ä\file', rule, profile=profile()),
                            normalize(r'C:\ä\file', rule, profile=profile()))

    def test_same_suffix_different_source_or_volume_remains_distinct(self):
        first = normalize(r'C:\Folder\file.bin', path_rule(), profile=profile())
        for axis, changed in [('image', 'different.E01'), ('exhibit', 'OTHER'),
                              ('source_snapshot', 'vss:fixture-copy'), ('source_variant', 'registry-backup:fixture')]:
            public = profile(); public['source_contexts']['volume']['origin'][axis] = changed
            self.assertNotEqual(first, normalize(r'C:\Folder\file.bin', path_rule(), profile=public))
        public = profile(); public['source_contexts']['volume']['volume']['value'] = '0123456789abcdee'
        self.assertNotEqual(first, normalize(r'C:\Folder\file.bin', path_rule(), profile=public))

    def test_path_unsafe_or_ambiguous_spellings_refuse(self):
        for value in [r'C:relative', r'Folder\file.bin', r'C:\A\..\file.bin', r'C:\.\file.bin',
                      r'C:\A\\file.bin', 'C:\\name.\\file', 'C:\\name \\file', r'C:\file:stream',
                      r'\\.\C:\file', r'\Device\HarddiskVolume1\file', r'\??\C:\file',
                      r'C:\*.bin', 'C:\\file\0', r'\\?\Volume{fixture}\file', 'C:\\\\', r'\device\HarddiskVolume1\file', r'\systemroot\file']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize(value, path_rule(), profile=profile())
        self.assertNotEqual(normalize('C:\\Folder', path_rule(), profile=profile()),
                            normalize('C:\\Folder\\', path_rule(), profile=profile()))

    def test_profile_config_versions_limits_and_unknown_keys_fail_closed(self):
        good = {'version': 1, 'fields': {'/values/*': {'kind': 'guid-v1'}}}
        self.assertEqual(validate_config(good, profile=profile()), good['fields'])
        with self.assertRaises(ValueError): validate_config(good)
        for bad in [dict(good, version=True), dict(good, version=2), dict(good, extra=True),
                    {'version': 1, 'fields': {}}, {'version': 1, 'fields': {'/bad~2pointer': {'kind': 'guid-v1'}}},
                    {'version': 1, 'fields': {'/' + '/'.join(['x'] * 17): {'kind': 'guid-v1'}}}]:
            with self.assertRaises(ValueError): validate_config(bad, profile=profile())
        for bad in [{'kind': []}, {'kind': 'browser-alias-v1'}, {'kind': 'guid-v1', 'trim': True},
                    {'kind': 'zone-label-offset-v1', 'label_mode': 'prefix'}, path_rule(context='absent'),
                    path_rule(case_sensitive=1)]:
            with self.assertRaises(ValueError): validate_rule(bad, profile=profile())
        for modify in [lambda p: p.update(version=True), lambda p: p.update(extra=True),
                       lambda p: p['source_contexts']['volume']['origin'].pop('source_variant'),
                       lambda p: p['source_contexts']['volume']['origin'].update(source_snapshot='unknown'),
                       lambda p: p['source_contexts']['volume']['origin'].update(image='\ud800'),
                       lambda p: p['source_contexts']['volume'].update(absolute_roots=['C:', 'c:']),
                       lambda p: p['source_contexts']['volume'].update(absolute_roots=['C:\\not-a-root']),
                       lambda p: p['source_contexts']['volume'].update(mapping_receipt_sha256='x' * 64)]:
            bad = profile(); modify(bad)
            with self.assertRaises(ValueError): validate_profile(bad)

    def test_normalization_does_not_modify_inputs_and_does_not_offer_browser_aliases(self):
        public, rule = profile(), path_rule()
        original = deepcopy(public), deepcopy(rule)
        normalize(r'C:\Folder\file.bin', rule, profile=public)
        self.assertEqual((public, rule), original)
        for label in ['Generic Browser', 'Generic Browser 9']:
            with self.assertRaises(ValueError): normalize(label, {'kind': 'guid-v1'})
        for value in [True, {}, [], '\ud800', 'x' * 32769]:
            with self.assertRaises(ValueError): normalize(value, {'kind': 'guid-v1'})


class BenchmarkNormalizationIntegration(unittest.TestCase):
    def config(self, fields=None, **extra):
        return dict({'normalization_profile': profile(), 'normalization': {
            'version': 1, 'fields': {'': {'kind': 'guid-v1'}} if fields is None else fields}}, **extra)

    def test_opt_in_both_directions_and_legacy_exact_unchanged(self):
        from eval.benchmark import Matcher
        left, right = '01234567-89ab-cdef-0123-456789abcdef', '{0123456789ABCDEF0123456789ABCDEF}'
        self.assertEqual([row['status'] for row in Matcher().compare(left, right)], ['missing', 'wrong'])
        matcher = Matcher(self.config())
        for expected, actual in ((left, right), (right, left)):
            matcher.validate_expected(expected)
            events = matcher.compare(expected, actual)
            self.assertEqual([row['status'] for row in events], ['match'])
            self.assertEqual(events[0]['expected'], expected)
            self.assertEqual(events[0]['actual'], actual)
        # Global legacy casefold does not leak into typed zone labels.
        matcher = Matcher(self.config({'': {'kind': 'zone-label-offset-v1'}}, strings='casefold'))
        self.assertNotEqual(matcher.compare('Fixture (UTC+01:00)', 'fixture (UTC+01:00)')[0]['status'], 'match')

    def test_wildcard_unordered_lists_preserve_multiplicity_and_extras(self):
        from eval.benchmark import Matcher
        matcher = Matcher(self.config({'/*': {'kind': 'guid-v1'}}, list_order='unordered'))
        a, b = '1' * 32, '2' * 32
        expected = [a, b]
        matcher.validate_expected(expected)
        self.assertEqual([event['status'] for event in matcher.compare(expected, ['{' + b + '}', a])], ['match', 'match'])
        duplicate = matcher.compare(expected, [a, '{' + a + '}'])
        self.assertEqual([event['status'] for event in duplicate].count('match'), 1)
        self.assertIn('missing', [event['status'] for event in duplicate])
        extra = matcher.compare(expected, [a, b, '{' + a + '}'])
        self.assertEqual([event['status'] for event in extra].count('match'), 2)
        self.assertEqual([event['status'] for event in extra].count('wrong'), 1)

    def test_malformed_actual_is_wrong_without_repair_invalid_expected_refuses(self):
        from eval.benchmark import Matcher
        matcher = Matcher(self.config())
        valid = '1' * 32
        matcher.validate_expected(valid)
        actual = ' ' + valid
        events = matcher.compare(valid, actual)
        self.assertEqual([event['status'] for event in events], ['missing', 'wrong'])
        self.assertEqual(events[1]['actual'], actual)
        with self.assertRaises(ValueError): matcher.validate_expected(actual)

    def test_profile_pair_overlap_unused_and_ambiguous_rules_refuse(self):
        from eval.benchmark import Matcher
        for bad in [{'normalization': self.config()['normalization']},
                    {'normalization_profile': profile()}, self.config(strings='prefix'),
                    self.config({'/field': {'kind': 'guid-v1'}}, string_modes={'/field': 'casefold'}),
                    self.config({'/field': {'kind': 'guid-v1'}}, string_aliases={'/field': [['A', 'B']]}),
                    self.config({'/field': {'kind': 'guid-v1'}}, paths={'': {'style': 'windows'}}),
                    self.config({'/field': {'kind': 'guid-v1'}}, timestamps={'': {}}),
                    self.config({'/items/*': {'kind': 'guid-v1'}}, list_rules={'/items': {'mode': 'subset', 'count': 1}})]:
            with self.subTest(config=bad), self.assertRaises(ValueError): Matcher(bad)
        matcher = Matcher(self.config({'/missing': {'kind': 'guid-v1'}}))
        with self.assertRaisesRegex(ValueError, 'does not address'): matcher.validate_expected({'present': '1' * 32})
        matcher = Matcher(self.config({'/*/x': {'kind': 'guid-v1'}, '/items/*': {'kind': 'zone-label-offset-v1'}}))
        with self.assertRaisesRegex(ValueError, 'ambiguous'):
            matcher.validate_expected({'items': {'x': '1' * 32}})

    def test_score_extension_hash_only_with_opt_in_and_original_values_preserved(self):
        import hashlib
        from pathlib import Path
        from eval import benchmark, match_normalization
        from tests.test_benchmark import reference, answers
        value, spelling = '1' * 32, '{' + '1' * 32 + '}'
        legacy = benchmark.score(reference(value), answers(value))
        self.assertNotIn('matching_extensions', legacy)
        public = reference(value)
        public['questions'][0]['match'] = self.config()
        result = benchmark.score(public, answers(spelling))
        self.assertEqual(result['question_counts']['fully_correct'], 1)
        extension = result['matching_extensions']['typed-representation-v1']
        self.assertEqual(extension['question_ids'], ['1'])
        self.assertEqual(extension['implementation_sha256'], hashlib.sha256(Path(match_normalization.__file__).read_bytes()).hexdigest())
        self.assertEqual(result['questions'][0]['audit'][0]['expected'], value)
        self.assertEqual(result['questions'][0]['audit'][0]['actual'], spelling)
        self.assertEqual(public['questions'][0]['expected'], value)
