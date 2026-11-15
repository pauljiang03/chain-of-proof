"""Prospective Q44 source-row gates; synthetic evidence only, no case proof."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from agent.answer_projection import claim_digest, project_answers
from checker.catalog import ROLES
from checker.check import check
from checker.facts import JsonFacts
from tests.fixtures.contracts.scope_contract import apply_data_leakage_scopes
from extractor.attributes import emit_attribute
from extractor.store import Evidence
from verifier.verify import verify

ROOT = Path(__file__).resolve().parents[1]
ROLES_ORDER = ['search.index.item_url', 'search.index.date_modified', 'search.index.store',
               'search.index.container_path', 'search.index.table', 'search.index.document_id']
URL = 'https://synthetic.invalid/full/path?q=unaltered%20text#fragment'
START = '2015-03-22T04:00:00Z'
STOP = '2015-03-24T04:00:00Z'


class SearchIEPublicFields(unittest.TestCase):
    def fixture(self, stamp='2015-03-23T03:59:59.1234567Z', variant='valid'):
        part = json.loads((ROOT/'tests/fixtures/contracts/data-leakage/parts/q41_60.json').read_text())
        question = next(q for q in part['questions'] if q['id'] == 'Q44')
        apply_data_leakage_scopes([question], json.loads((ROOT/'tests/fixtures/contracts/data-leakage/scope_plan.json').read_text()))
        origin = deepcopy(question['answer_schema']['x-claim-scope']['origins'][0])
        if variant == 'foreign': origin.update(image='foreign.E01', exhibit='FOREIGN')
        if variant == 'backup': origin['source_variant'] = 'registry-backup:synthetic'
        roles = list(ROLES_ORDER)
        values = [URL, stamp, 'iehistory', r'C:\Search\Windows.edb', 'SystemIndex_0A', 42]
        if variant == 'other_store': values[2] = 'other-store'
        if variant == 'store_case': values[2] = 'IEHistory'
        if variant == 'created': roles[1] = 'search.index.date_created'
        evidence = Evidence(); identities = []
        for index, (role, value) in enumerate(zip(roles, values)):
            subject = 'container-B:doc42' if variant == 'mixed' and index == 3 else 'container-A:doc42'
            identities.append(emit_attribute(evidence, subject, role, value, 100,
                                            artifact='synthetic native Search row', **origin))
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup); root = Path(temp.name)
        evidence.write_json(root/'facts.json', {}); facts = JsonFacts(root/'facts.json'); entries = []
        for role, identity in zip(roles, identities):
            records = {f.kind:f.id for f in facts.all() if facts.string(f.obj) == identity}
            spec = ROLES[role]
            entries.append([records['attributeSubject'], records[spec.kind], records[spec.value_kind], role])
        if variant == 'missing': entries.pop()
        if variant == 'duplicate': entries.append(deepcopy(entries[2]))
        row = dict(candidate_id='IE', claim={'attributeTuple':entries})
        bindings = [dict(candidate_id='IE', claim_sha256=claim_digest(row['claim']), question_id='Q44',
                         path=['records', 0, field], part=0, field='value_'+str(i))
                    for i, field in [(0, 'url'), (1, 'date_modified')]]
        result = project_answers(dict(schema_version=2, case_id='synthetic-ie', questions=[question]),
            [row], bindings, facts, require_claim_requirements=True, require_evidence_scope=True,
            evidence_facts_sha256=hashlib.sha256((root/'facts.json').read_bytes()).hexdigest())
        return result, row, facts, root

    def test_synthetic_tuple_kernel_replay_and_strict_projection_preserve_native_values(self):
        stamp = '2015-03-23T03:59:59.1234567Z'
        result, row, facts, root = self.fixture(stamp)
        self.assertFalse(result['unsupported'])
        self.assertEqual(result['submission']['answers'][0]['answer'],
                         {'records':[{'url':URL, 'date_modified':stamp}]})
        cert = check(row['claim'], 'IESynthetic', facts, out_dir=root)
        self.assertEqual(cert['status'], 'verified', cert)
        self.assertEqual(verify(cert, facts), [])

    def test_exact_100ns_half_open_boundaries_and_both_local_days(self):
        for stamp, accepted in [
                ('2015-03-22T03:59:59.9999999Z', False), (START, True),
                ('2015-03-22T04:00:00.0000001Z', True),
                ('2015-03-23T04:00:00Z', True),
                ('2015-03-24T03:59:59.9999999Z', True), (STOP, False),
                ('2015-03-24T04:00:00.0000001Z', False),
                ('2015-03-22T00:00:00-04:00', True),
                ('2015-03-24T00:00:00-04:00', False)]:
            with self.subTest(stamp=stamp):
                result, _, _, _ = self.fixture(stamp)
                self.assertEqual(bool(result['leaves']), accepted)
                if accepted:
                    self.assertEqual(result['submission']['answers'][0]['answer']['records'][0]['date_modified'], stamp)

    def test_same_url_wrong_store_wrong_column_missing_duplicate_and_wrong_origin_refuse(self):
        for variant in ('other_store', 'store_case', 'created', 'missing', 'duplicate', 'foreign', 'backup'):
            with self.subTest(variant=variant):
                result, _, _, _ = self.fixture(variant=variant)
                self.assertFalse(result['leaves'])
                self.assertTrue(result['unsupported'])

    def test_foreign_container_subject_cannot_certify(self):
        _, row, facts, root = self.fixture(variant='mixed')
        cert = check(row['claim'], 'IEMixed', facts, out_dir=root)
        self.assertNotEqual(cert['status'], 'verified', cert)

    def test_native_timestamp_unknown_or_excess_precision_cannot_supply_url(self):
        for stamp in ('2015-03-23T04:00:00', '2015-03-23T04:00:00-00:00',
                      '2015-03-23T04:00:00.12345678Z'):
            with self.subTest(stamp=stamp):
                result, _, _, _ = self.fixture(stamp)
                self.assertFalse(result['leaves'])
                self.assertTrue(result['unsupported'])
