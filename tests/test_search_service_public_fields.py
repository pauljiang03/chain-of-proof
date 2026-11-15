"""Q42 service-only literals: native selected-control-set reader through public projection."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from agent.answer_projection import claim_digest, project_answers
from checker.catalog import ROLES
from checker.check import check
from checker.facts import JsonFacts
from eval.data_leakage_strict_draft.scope_contract import apply_data_leakage_scopes
from extractor import structured_system as reader, system
from extractor.attributes import emit_attribute
from extractor.store import Evidence
from verifier.verify import verify

ROOT = Path(__file__).resolve().parents[1]
ROLES_ORDER = ['search.service.registry_key', 'search.service.start_code', 'search.service.start_type']
ORIGIN = dict(image='pc.E01', exhibit='PC', source_snapshot='base-volume', source_variant='primary')


def native_value(name, value, kind=4): return NS(name=name, value=value, type=kind)


class SearchServicePublicFields(unittest.TestCase):
    def native(self, *, current=2, existing=(1, 2), service='WSearch', service_set=2, code=2, kind=4, origin=None):
        origin = origin or ORIGIN
        root = NS(path='', subkeys=lambda: [NS(name='ControlSet%03d' % i) for i in existing])
        hive = system.Hive('SYSTEM', NS(root=lambda: root), r'C:\Windows\System32\config\SYSTEM', False, None, None)
        opened = []
        def open_key(ev, h, path):
            opened.append(path)
            if path == 'Select':
                return NS(path=path, values=lambda: [] if current is None else [native_value('Current', current)])
            if path == 'ControlSet%03d\\Services\\%s' % (service_set, service):
                return NS(path=path, values=lambda: [native_value('Start', code, kind)])
            return None
        evidence = Evidence()
        with patch.object(system, '_hives', return_value=[hive]), patch.object(system, '_open', side_effect=open_key):
            reader.registry(evidence, None, dict(common=origin, examined_at=100))
        return evidence, opened

    def project(self, evidence, variant='valid'):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup); root = Path(temp.name)
        evidence.write_json(root/'facts.json', {}); facts = JsonFacts(root/'facts.json')
        entries = []
        for role in ROLES_ORDER:
            value_fact = next(f for f in facts.all() if f.kind == ROLES[role].value_kind and
                              f.prov.get('attribute_role') == role)
            identity = facts.string(value_fact.obj)
            records = {f.kind:f.id for f in facts.all() if facts.string(f.obj) == identity}
            spec = ROLES[role]
            entries.append([records['attributeSubject'], records[spec.kind], records[spec.value_kind], role])
        if variant == 'missing': entries.pop(1)
        row = dict(candidate_id='Service', claim={'attributeTuple':entries})
        part = json.loads((ROOT/'eval/data_leakage_strict_draft/parts/q41_60.json').read_text())
        question = next(q for q in part['questions'] if q['id'] == 'Q42')
        apply_data_leakage_scopes([question], json.loads((ROOT/'eval/data_leakage_strict_draft/scope_plan.json').read_text()))
        bindings = [dict(candidate_id='Service', claim_sha256=claim_digest(row['claim']), question_id='Q42',
                         path=['identification', field], part=0, field='value_'+str(i))
                    for i, field in [(0, 'service_registry_key'), (2 if variant != 'missing' else 1, 'startup')]]
        result = project_answers(dict(schema_version=2, case_id='synthetic-service', questions=[question]),
            [row], bindings, facts, require_claim_requirements=True, require_evidence_scope=True,
            evidence_facts_sha256=hashlib.sha256((root/'facts.json').read_bytes()).hexdigest())
        return result, row, facts, root

    def test_actual_reader_tuple_kernel_and_public_partial_configuration(self):
        evidence, opened = self.native()
        result, row, facts, root = self.project(evidence)
        self.assertFalse(result['unsupported'])
        self.assertEqual(result['submission']['answers'][0]['answer'], {'identification':{
            'service_registry_key':r'HKLM\SYSTEM\ControlSet002\Services\WSearch', 'startup':'SERVICE_AUTO_START'}})
        self.assertIn(r'ControlSet002\Services\WSearch', opened)
        self.assertNotIn(r'ControlSet001\Services\WSearch', opened)
        cert = check(row['claim'], 'ServiceValid', facts, out_dir=root)
        self.assertEqual(cert['status'], 'verified', cert)
        self.assertEqual(verify(cert, facts), [])

    def test_native_start_enum_is_fixed_for_all_reviewed_codes(self):
        for code, expected in reader.SERVICE_START_TYPES.items():
            evidence, _ = self.native(code=code)
            observed = [json.loads(value) for kind, _, _, _, value, raw in evidence.rows()
                        if kind == 'attributeTextValue' and json.loads(raw).get('attribute_role') == 'search.service.start_type']
            self.assertEqual(observed, [expected])

    def test_native_wrong_service_unselected_missing_dangling_and_bad_type_emit_no_service(self):
        for options in [dict(service='OtherService'), dict(service_set=1), dict(current=None),
                        dict(current=3), dict(current=True), dict(code='2'), dict(code='2', kind=1)]:
            with self.subTest(options=options):
                evidence, _ = self.native(**options)
                self.assertFalse(any(kind.startswith('attribute') for kind, *_ in evidence.rows()))

    def test_foreign_scope_and_missing_role_cannot_supply_partial_key(self):
        for options, variant in [(dict(origin=dict(ORIGIN, source_variant='registry-backup:fixture')), 'valid'),
                                 ({}, 'missing')]:
            evidence, _ = self.native(**options)
            result, _, _, _ = self.project(evidence, variant)
            self.assertFalse(result['leaves'])
            self.assertTrue(result['unsupported'])

    def test_same_subject_code_label_provenance_is_reader_trust_boundary(self):
        # Deliberately forged extraction illustrates the declared boundary: Lean
        # proves typed facts, not raw Start bytes or the reader's enum function.
        evidence = Evidence()
        values = [r'HKLM\SYSTEM\ControlSet002\Services\WSearch', 2, 'SERVICE_DISABLED']
        for role, value in zip(ROLES_ORDER, values):
            emit_attribute(evidence, 'forged:one-occurrence', role, value, 100,
                           artifact='synthetic untrusted extractor', **ORIGIN)
        result, row, facts, root = self.project(evidence)
        self.assertFalse(result['unsupported'])
        cert = check(row['claim'], 'TrustBoundary', facts, out_dir=root)
        self.assertEqual(cert['status'], 'verified', cert)

    def test_cross_subject_tuple_fails_kernel(self):
        evidence = Evidence()
        for i, (role, value) in enumerate(zip(ROLES_ORDER, [r'HKLM\SYSTEM\ControlSet002\Services\WSearch', 2, 'SERVICE_AUTO_START'])):
            emit_attribute(evidence, 'row-other' if i == 2 else 'row-one', role, value, 100,
                           artifact='synthetic mixed registry', **ORIGIN)
        _, row, facts, root = self.project(evidence)
        cert = check(row['claim'], 'MixedService', facts, out_dir=root)
        self.assertNotEqual(cert['status'], 'verified', cert)
