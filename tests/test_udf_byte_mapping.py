"""Known-byte UDF invariants across physical layouts and allocation-table states.

Expected content is built before the bytes are placed; the oracle never calls
Udf.physical, runs, pieces or the cache.
"""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import unittest

from extractor import optical as o
from extractor.content import _disc_rows
from extractor.store import Evidence
from tests.test_optical import efe, long_ad, tag


S = o.SECTOR
CTX = {'common': {'image': 'synthetic-virtual.img', 'exhibit': 'DISC', 'tool': 'known-byte fixture',
                  'source_snapshot': 'optical-image', 'source_variant': 'primary'},
       'examined_at': 1800000000000000}


def fixture(sectors, mappings, *, start=0, partition_size=64, image_sectors=64):
    disk = bytearray(image_sectors * S)
    for number, payload in sectors.items():
        if len(payload) != S:
            raise ValueError('fixture sector must contain exactly one sector of known bytes')
        disk[number * S:(number + 1) * S] = payload
    reads = []
    def read(sector, count):
        reads.append((sector, count))
        return bytes(disk[sector * S:(sector + count) * S])
    udf = o.Udf(read, image_sectors)
    udf.partitions = {0: (start, partition_size)}
    udf.lvd = o.Lvd(1, 'FIXTURE', S, '2.01', o.Extent(0, S, 0, 1),
                    (o.PartitionMap('physical', 0), o.PartitionMap('virtual', 0)))
    udf.versions = [o.Version(30 + i, o.Vat(tuple(mapping), None, 'FIXTURE', None, None),
                              None, serial=0x12345678) for i, mapping in enumerate(mappings)]
    return udf, reads


def mapping(*physical):
    return [o.UNMAPPED] * 10 + list(physical)


def entry(size, *, descriptors=None, embedded=None, unique=42, file_type=o.FT_FILE):
    data = long_ad(size, 10, 1) if descriptors is None else descriptors
    if embedded is not None:
        data = embedded
    return o.parse_file_entry(efe(2, file_type, size, unique, data, 3 if embedded is not None else 1))


def listed(path, native, version=0, sector=2):
    return o.Listed(path, False, native, sector, 1, 1, version)


def survey(udf, current, recovered=(), unreadable=()):
    return o.Survey(udf, {'sessions': [], 'close': lambda: None}, list(current),
                    [(item, {}) for item in recovered], [], frozenset(unreadable))


def hashes(s):
    evidence = Evidence()
    _disc_rows(evidence, Path('synthetic-virtual.img'), CTX, s, 'UTC')
    return {row[3]: (row[4], json.loads(row[-1])) for row in evidence.rows() if row[0] == 'fileContent'}, evidence


class VirtualByteMappings(unittest.TestCase):
    def test_audit_noncontiguous_virtual_extent_reads_known_bytes(self):
        expected = b'A' * S + b'B' * S
        udf, reads = fixture({4: b'A' * S, 5: b'Z' * S, 9: b'B' * S}, [mapping(4, 9)])
        file = listed(r'\virtual.bin', entry(len(expected)))
        s = survey(udf, [file])
        self.assertEqual(udf.runs(file.entry, 1, s.vat(file)), [(4, S), (9, S)])
        self.assertEqual(b''.join(s.content(file)), expected)
        records, evidence = hashes(s)
        self.assertEqual(evidence.problems, [])
        self.assertEqual(records[file.path][0], 'sha256:' + hashlib.sha256(expected).hexdigest())
        self.assertEqual(records[file.path][1]['first_sector'], 4)
        self.assertNotIn((4, 2), reads)

    def test_generated_layout_permutations_preserve_logical_bytes_and_partial_tails(self):
        # 6 physical layouts x 4 sizes include fragmentation, reverse order,
        # adjacency, one-byte tail and a truncated final logical block.
        logical = [b'A' * S, b'B' * S, b'C' * S]
        for layout, size in itertools.product(itertools.permutations((4, 5, 9)), (1, S, S + 1, 3 * S - 37)):
            with self.subTest(layout=layout, size=size):
                expected = b''.join(logical)[:size]
                udf, _ = fixture(dict(zip(layout, logical)), [mapping(*layout)])
                file = listed(r'\layout.bin', entry(size))
                self.assertEqual(b''.join(survey(udf, [file]).content(file)), expected)

    def test_coalesces_only_physically_adjacent_full_blocks(self):
        udf, _ = fixture({4: b'A' * S, 5: b'B' * S, 9: b'C' * S}, [mapping(4, 5, 9)])
        native = entry(2 * S + 7)
        self.assertEqual(udf.runs(native, 1, udf.versions[0].vat), [(4, 2 * S), (9, 7)])
        # Adjacent sectors separated by a partially used block are not adjacent bytes.
        native = entry(8, descriptors=long_ad(3, 10, 1) + long_ad(5, 11, 1))
        self.assertEqual(udf.runs(native, 1, udf.versions[0].vat), [(4, 3), (5, 5)])
        self.assertEqual(b''.join(udf.pieces(native, 1, udf.versions[0].vat)), b'AAA' + b'BBBBB')

    def test_every_later_virtual_block_is_required_before_data_is_yielded(self):
        for bad_map in (mapping(4, o.UNMAPPED), mapping(4), mapping(4, 64), mapping(4, -1)):
            with self.subTest(mapping=bad_map):
                udf, reads = fixture({4: b'A' * S}, [bad_map])
                with self.assertRaises((LookupError, ValueError)):
                    next(udf.pieces(entry(2 * S), 1, udf.versions[0].vat))
                self.assertEqual(reads, [])

    def test_translated_blocks_are_checked_against_partition_and_image_bounds(self):
        for start, length, mapped in ((0, 8, 9), (60, 8, 5)):
            with self.subTest(start=start, length=length):
                udf, _ = fixture({}, [mapping(mapped)], start=start, partition_size=length)
                with self.assertRaises(LookupError):
                    list(udf.pieces(entry(1), 1, udf.versions[0].vat))
        udf, _ = fixture({}, [mapping(4)])
        for block, part in ((-1, 1), (1, -1), (1, 2)):
            with self.assertRaises(LookupError):
                udf.physical(block, part, udf.versions[0].vat)

    def test_unreadable_translated_second_block_prevents_partial_hash(self):
        udf, reads = fixture({4: b'A' * S, 9: b'B' * S}, [mapping(4, 9)])
        file = listed(r'\unreadable.bin', entry(2 * S))
        s = survey(udf, [file], unreadable=[9])
        with self.assertRaises(ValueError):
            next(s.content(file))
        self.assertEqual(reads, [])
        records, evidence = hashes(s)
        self.assertEqual(records, {})
        self.assertTrue(evidence.problems)
        # Sector 5 is not part of this file and must not block its actual bytes.
        self.assertEqual(b''.join(survey(udf, [file], unreadable=[5]).content(file)), b'A' * S + b'B' * S)

    def test_sparse_holes_do_not_request_unmapped_virtual_blocks(self):
        udf, _ = fixture({4: b'A' * S, 9: b'B' * S}, [mapping(4, 9)])
        descriptors = long_ad(S, 10, 1) + long_ad((2 << 30) | 17, 999, 1) + long_ad(S, 11, 1)
        native = entry(2 * S + 17, descriptors=descriptors)
        self.assertEqual(b''.join(udf.pieces(native, 1, udf.versions[0].vat)), b'A' * S + bytes(17) + b'B' * S)

    def test_multiblock_allocation_descriptor_uses_the_same_virtual_mapping(self):
        descriptors = long_ad(1, 20, 0) * 127 + long_ad(1, 21, 0)
        continuation = tag(o.TAG_AED, struct.pack('<II', 0, len(descriptors)) + descriptors, 10)
        payload = continuation + bytes(2 * S - len(continuation))
        udf, _ = fixture({4: payload[:S], 5: b'Z' * S, 9: payload[S:],
                          20: b'A' * S, 21: b'B' * S}, [mapping(4, 9)])
        native = entry(128, descriptors=long_ad((3 << 30) | len(continuation), 10, 1))
        self.assertEqual(b''.join(udf.pieces(native, 1, udf.versions[0].vat)), b'A' * 127 + b'B')
        with self.assertRaises(ValueError):
            list(udf.pieces(native, 1, udf.versions[0].vat, frozenset([9])))

    def test_truncated_continuation_is_not_a_partial_file(self):
        body = struct.pack('<II', 0, 32) + long_ad(1, 20, 0)
        truncated = tag(o.TAG_AED, body, 10)
        udf, _ = fixture({4: truncated + bytes(S - len(truncated)), 20: b'A' * S}, [mapping(4)])
        native = entry(1, descriptors=long_ad((3 << 30) | len(truncated), 10, 1))
        with self.assertRaises(ValueError):
            list(udf.pieces(native, 1, udf.versions[0].vat))


class AllocationStateContentCache(unittest.TestCase):
    def test_audit_old_and_new_vats_keep_distinct_hashes_and_physical_provenance(self):
        udf, _ = fixture({4: b'A' * S, 9: b'B' * S}, [mapping(4), mapping(9)])
        old = listed(r'\old.bin', entry(S), version=0, sector=2)
        new = listed(r'\new.bin', entry(S, unique=43), version=1, sector=3)
        records, evidence = hashes(survey(udf, [new], [old]))
        self.assertEqual(evidence.problems, [])
        for file, payload, sector in ((old, b'A' * S, 4), (new, b'B' * S, 9)):
            digest, provenance = records[file.path]
            self.assertEqual(digest, 'sha256:' + hashlib.sha256(payload).hexdigest())
            self.assertEqual(provenance['first_sector'], sector)
            self.assertEqual(provenance['allocation_version_index'], file.version)
            self.assertEqual(provenance['allocation_table_at_sector'], 30 + file.version)
        self.assertNotEqual(records[old.path][0], records[new.path][0])

    def test_generated_versions_and_processing_orders_match_known_source_bytes(self):
        sectors = {4: b'A' * S, 5: b'B' * S, 9: b'C' * S}
        layouts = list(itertools.permutations(sectors, 2))
        # 36 pairs of allocation states x two processing orders. Their virtual
        # descriptors are deliberately identical while their physical bytes vary.
        for old_layout, new_layout, reverse in itertools.product(layouts, layouts, (False, True)):
            with self.subTest(old=old_layout, new=new_layout, reverse=reverse):
                udf, _ = fixture(sectors, [mapping(*old_layout), mapping(*new_layout)])
                files = [listed(r'\version0.bin', entry(S + 19), 0, 2),
                         listed(r'\version1.bin', entry(S + 19, unique=43), 1, 3)]
                records, evidence = hashes(survey(udf, reversed(files) if reverse else files))
                self.assertEqual(evidence.problems, [])
                for file, layout in zip(files, (old_layout, new_layout)):
                    expected = sectors[layout[0]] + sectors[layout[1]][:19]
                    self.assertEqual(records[file.path][0], 'sha256:' + hashlib.sha256(expected).hexdigest())
                    self.assertEqual(records[file.path][1]['first_sector'], layout[0])

    def test_unmapped_old_state_cannot_reuse_a_valid_new_state_digest(self):
        udf, _ = fixture({4: b'A' * S, 9: b'B' * S}, [mapping(4, o.UNMAPPED), mapping(4, 9)])
        old = listed(r'\old.bin', entry(2 * S), 0, 2)
        new = listed(r'\new.bin', entry(2 * S, unique=43), 1, 3)
        records, evidence = hashes(survey(udf, [new], [old]))
        self.assertEqual(set(records), {new.path})
        self.assertTrue(evidence.problems)


if __name__ == '__main__':
    unittest.main()
