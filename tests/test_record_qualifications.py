"""Source timestamp roles and recovery limitations survive claim rendering."""
import copy
import hashlib
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from checker.check import check
from checker.facts import JsonFacts
from extractor import webcloud
from extractor.content import _row
from extractor.store import Evidence
from tests.test_inventory import FS
from tests.test_sticky_note_fields import OLE_STORAGE_TIME, SNT_SOURCE, snt_bytes
from verifier.verify import verify

BASE = 1_767_225_600_000_000  # 2026-01-01 UTC
COMMON = {'image': 'synthetic.E01', 'exhibit': 'EXAMPLE', 'source_snapshot': 'base-volume',
          'source_variant': 'primary', 'tool': 'synthetic qualification test'}


class RecordQualifications(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.sequence = 0

    def source(self, evidence, name):
        path = self.root / (name + '.json')
        evidence.write_json(path, {})
        return JsonFacts(path)

    def certify(self, source, claim, accepted=True):
        self.sequence += 1
        cert = check(claim, f'Qualification{self.sequence}', source, out_dir=self.root)
        self.assertEqual(cert['status'], 'verified' if accepted else 'rejected', cert)
        if accepted:
            self.assertEqual(cert['axioms'], [])
            self.assertEqual(cert['trust_tier'], 'kernel')
            self.assertEqual(verify(cert, source), [])
        return cert

    def test_actual_ole_note_reader_keeps_container_and_storage_time_meanings(self):
        fs = FS()
        container_seconds = BASE // 1_000_000 + 86400
        fs.add(SNT_SOURCE, data=snt_bytes(), modified=container_seconds)
        evidence = Evidence()
        with patch.object(webcloud, '_users', return_value=[('Example', fs.path('C:/Users/Example'))]):
            webcloud._sticky_notes(evidence, SimpleNamespace(fs=fs), COMMON)
        self.assertEqual(evidence.problems, [])
        source = self.source(evidence, 'notes')
        notes = [row for row in source.all() if row.kind == 'noteText']
        self.assertEqual(len(notes), 2)
        expected = {
            container_seconds * 1_000_000: 'last-modified time of the Sticky Notes file',
            (OLE_STORAGE_TIME - 116444736000000000) // 10:
                "modified time of this note's storage inside the Sticky Notes file"}
        self.assertEqual({row.t: row.prov['time_meaning'] for row in notes}, expected)
        self.assertEqual(len({row.obj for row in notes}), 1)
        for row in notes:
            with self.subTest(source_time_meaning=row.prov['time_meaning']):
                cert = self.certify(source, {'noteFound': [row.id]})
                self.assertIn('retained Sticky Notes record contains note text', cert['english'])
                self.assertIn(row.prov['time_meaning'], cert['english'])
                self.assertIn(row.prov['artifact'], cert['english'])
                self.assertIn('not a note-editing action, its time, or its author', cert['english'])
                self.assertNotIn('(last modified ', cert['english'])
                altered = copy.deepcopy(cert)
                altered['english'] = 'The note was edited on 2026-01-02.'
                self.assertTrue(verify(altered, source))

    def test_note_without_timestamp_meaning_remains_explicitly_unknown(self):
        evidence = Evidence()
        evidence.add('noteText', BASE, 1, 'Literal text', 'Note app', **COMMON)
        source = self.source(evidence, 'unknown-note')
        cert = self.certify(source, {'noteFound': [source.all()[0].id]})
        self.assertIn('unspecified record timestamp', cert['english'])
        self.assertIn('source artifact: not supplied', cert['english'])
        self.assertNotIn('(last modified ', cert['english'])

    def test_comparison_keeps_both_recovered_read_procedures_and_layout_limits(self):
        data = b'A' * 512 + b'Z' * 512
        digest = hashlib.sha256(data).hexdigest()
        evidence = Evidence()
        ctx = {'common': COMMON, 'examined_at': BASE + 86400_000_000}
        procedures = (
            'one contiguous run of 2 clusters; the allocation table no longer describes this file, so a fragmented file would hash wrongly',
            'one contiguous run of 4 clusters in an older derived layout; cluster chain unknown')
        for index, (procedure, layout) in enumerate(zip(procedures, ('current', 'older-derived')), start=1):
            _row(evidence, ctx, f'\\recovered-{index}.txt', digest, len(data), data,
                 'recorded recovery area', f'FAT directory entry source {index}', recovered=True,
                 source_variant='unallocated-recovery', layout=layout, read_as=procedure)
        _row(evidence, ctx, '\\allocated.txt', digest, len(data), data, 'volume-A',
             'allocated file read through its run list')
        _row(evidence, ctx, '\\different.txt', hashlib.sha256(b'other').hexdigest(), 5,
             b'other', 'volume-A', 'allocated other file')
        source = self.source(evidence, 'content')
        by_path = {source.string(row.obj): row for row in source.all() if row.kind == 'fileContent'}
        first, second, allocated, different = (by_path[path] for path in
            ('\\recovered-1.txt', '\\recovered-2.txt', '\\allocated.txt', '\\different.txt'))
        cert = self.certify(source, {'sameContent': [first.id, second.id]})
        self.assertIn('same recorded content hash', cert['english'])
        self.assertNotIn('identical content', cert['english'])
        for row, procedure, layout in zip((first, second), procedures, ('current', 'older-derived')):
            self.assertIn(f'For content record {row.id} ({source.string(row.obj)} on exhibit EXAMPLE)', cert['english'])
            self.assertIn(procedure, cert['english'])
            self.assertIn(f'({layout} layout)', cert['english'])
        self.assertEqual(cert['english'].count('If that space was reused since'), 2)
        # Argument order cannot silently drop a recovered record's caveat.
        for ids in ([first.id, allocated.id], [allocated.id, first.id]):
            mixed = self.certify(source, {'sameContent': ids})
            self.assertIn(procedures[0], mixed['english'])
            self.assertIn('If that space was reused since', mixed['english'])
        self.certify(source, {'sameContent': [first.id, different.id]}, accepted=False)
        altered = copy.deepcopy(cert)
        altered['english'] = cert['english'].split(' For content record ', 1)[0]
        self.assertTrue(verify(altered, source))


if __name__ == '__main__':
    unittest.main()
