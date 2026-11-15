"""A cache sighting or file timestamp must never become an execution-time claim."""
import json
from pathlib import Path
import tempfile
import unittest

from checker import claims
from checker.check import check
from checker.facts import Fact, FactSource, JsonFacts
from verifier.verify import verify


class Source(FactSource):
    def __init__(self, provenance):
        self.row = Fact(1, 'programRun', 1_500_000_000_000_000, 1, 1, 2, provenance)

    def get(self, ids):
        return {1: self.row} if 1 in ids else {}

    def all(self):
        return [self.row]

    def string(self, sid):
        return {1: 'example.exe', 2: r'C:\tools\example.exe'}[sid]


def sentence(prov):
    src = Source(prov)
    return claims.english(claims.parse({'programRan': [1]}), {1: src.row}, src)


class ProgramObservations(unittest.TestCase):
    def test_shimcache_file_mtime_is_never_run_time_regardless_of_execution_flag(self):
        for flag in ('missing', None, False, True):
            prov = {'source': 'application compatibility cache',
                    'time_meaning': 'last-modified time of the file as stored in the compatibility cache; not a run time'}
            if flag != 'missing':
                prov['executed_flag'] = flag
            with self.subTest(flag=flag):
                text = sentence(prov)
                self.assertIn('last-modified time of the file', text)
                self.assertIn('does not establish execution at that time', text)
                self.assertNotIn('recorded execution time for', text)
                self.assertNotIn('example.exe ran', text)

    def test_unknown_cache_registry_and_task_records_remain_sightings(self):
        for source, meaning in [('', ''), ('RecentFileCache.bcf', 'last-modified time of RecentFileCache.bcf'),
                                ('MUICache', 'last-write time of the registry key'),
                                ('open/save dialog history', 'registry key last-write time'),
                                ('scheduled task (TaskCache)', 'last run time of the scheduled task whose action runs this program')]:
            with self.subTest(source=source):
                self.assertIn('does not establish execution at that time',
                              sentence({'source': source, 'time_meaning': meaning}))

    def test_execution_provenance_cannot_upgrade_the_legacy_kind(self):
        supported = [('prefetch', 'last run time in the prefetch header'),
                     ('prefetch', 'earlier run time 2 in the prefetch header'),
                     ('UserAssist', 'last run time stored in the UserAssist entry'),
                     ('Security event log: process creation', 'time the process was created')]
        for source, meaning in supported:
            prov = {'source': source, 'time_meaning': meaning, 'run_count': 42}
            with self.subTest(source=source, meaning=meaning):
                self.assertIn('application observation', sentence(prov))
                self.assertIn('source: ' + source, sentence(prov))
                self.assertIn(meaning, sentence(prov))
                self.assertNotIn('recorded execution time for', sentence(prov))
                self.assertIn('does not establish execution at that time', sentence(prov))
                self.assertNotIn('42', sentence(prov))
                for flag in (None, False, 0, 'true'):
                    self.assertIn('does not establish execution at that time', sentence(dict(prov, executed_flag=flag)))
        self.assertIn('does not establish execution at that time', sentence({'source': 'prefetch'}))

    def test_before_and_census_cannot_bypass_the_conservative_program_rendering(self):
        src = Source({'source': 'application compatibility cache', 'executed_flag': False,
                      'time_meaning': 'file last-modified time, not execution time'})
        text = claims.english(claims.parse({'before': [1, 1]}), {1: src.row}, src)
        self.assertIn('file last-modified time', text)
        self.assertNotIn('recorded run of', text)
        census = claims.english(claims.parse({'exactly': ['programRun', 1]}), {1: src.row}, src)
        self.assertIn('application-artifact', census)
        self.assertNotIn('program-run', census)

    def test_cautious_sentence_is_certified_and_verified_without_changing_the_legacy_kind(self):
        with tempfile.TemporaryDirectory() as directory:
            src = Source({'source': 'application compatibility cache', 'executed_flag': None,
                          'time_meaning': 'file last-modified time, not execution time'})
            cert = check({'programRan': [1]}, 'ApplicationObservation', src, out_dir=Path(directory))
            self.assertEqual(cert['status'], 'verified')
            self.assertEqual(verify(cert, src), [])
            self.assertEqual(cert['cited_facts'][0]['kind'], 'programRun')
            self.assertIn('does not establish execution at that time', cert['english'])


if __name__ == '__main__':
    unittest.main()
