"""Literal partition/configuration restorations use actual public source gates."""
import hashlib
import json
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from agent.answer_projection import claim_digest, project_answers
from checker.catalog import ROLES
from checker.check import check
from checker.facts import JsonFacts
from eval.data_leakage_strict_draft.scope_contract import apply_data_leakage_scopes
from extractor.attributes import emit_attribute
from extractor.store import Evidence

ROOT = Path(__file__).resolve().parents[1]
CASES = {
 'Q2': ('q01_20.json', ['number', 'bootable', 'filesystem', 'start_sector', 'total_sectors'],
        'partition.', [1, True, 'NTFS', 2048, 4096]),
 'Q50': ('q41_60.json', ['registry_key', 'value_name', 'pattern'], 'snapshot.exclusion.',
         [r'ControlSet001\Control\BackupRestore\FilesNotToSnapshot', 'OutlookOST', '*.ost'])}


class RestoredPublicLiterals(unittest.TestCase):
    def fixture(self, qid, variant='valid'):
        filename, fields, prefix, values = CASES[qid]
        roles = [prefix + field for field in fields]
        part = json.loads((ROOT/'eval/data_leakage_strict_draft/parts'/filename).read_text())
        question = next(q for q in part['questions'] if q['id'] == qid)
        plan = json.loads((ROOT/'eval/data_leakage_strict_draft/scope_plan.json').read_text())
        apply_data_leakage_scopes([question], plan)
        public = {'schema_version': 2, 'case_id': 'synthetic-literals', 'questions': [question]}
        origin = deepcopy(question['answer_schema']['x-claim-scope']['origins'][0])
        if qid == 'Q2':
            self.assertEqual((origin['source_snapshot'], origin['source_variant']),
                             ('evidence-image', 'logical-image'))
            # Match the real raw-MBR reader, independently of the selected policy.
            origin.update(source_snapshot='evidence-image', source_variant='logical-image')
        if variant == 'old_base': origin.update(source_snapshot='base-volume', source_variant='primary')
        if variant == 'foreign': origin.update(image='foreign.E01', exhibit='FOREIGN')
        if variant == 'wrong_name': values = list(values); values[1] = 'OtherApplication'
        ev = Evidence(); identities = []
        for index, (role, value) in enumerate(zip(roles, values)):
            subject = 'synthetic:other' if variant == 'mixed' and index == 0 else 'synthetic:row'
            identities.append(emit_attribute(ev, subject, role, value, 100,
                                            artifact='synthetic native source', **origin))
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        root = Path(temp.name); ev.write_json(root/'facts.json', {})
        source = JsonFacts(root/'facts.json'); entries = []
        for role, identity in zip(roles, identities):
            rows = {f.kind:f.id for f in source.all() if source.string(f.obj) == identity}
            spec = ROLES[role]
            entries.append([rows['attributeSubject'], rows[spec.kind], rows[spec.value_kind], role])
        if variant == 'missing': entries = entries[:-1]
        if variant == 'wrong_kind': entries[0][3] = roles[1]
        row = {'candidate_id': 'Literal', 'claim': {'attributeTuple': entries}}
        bindings = [dict(candidate_id='Literal', claim_sha256=claim_digest(row['claim']), question_id=qid,
                         path=['partitions', 0, field] if qid == 'Q2' else [field], part=0,
                         field='value_'+str(index)) for index, field in enumerate(fields[:1] if variant == 'missing' else fields)]
        result = project_answers(public, [row], bindings, source, require_claim_requirements=True,
                                 require_evidence_scope=True,
                                 evidence_facts_sha256=hashlib.sha256((root/'facts.json').read_bytes()).hexdigest())
        return result, row, source, root

    def test_valid_literals_survive_without_size_or_causation(self):
        for qid in CASES:
            with self.subTest(qid=qid):
                result, row, source, root = self.fixture(qid)
                self.assertFalse(result['unsupported'])
                self.assertEqual(len(result['leaves']), len(CASES[qid][1]))
                answer = result['submission']['answers'][0]['answer']
                actual = answer['partitions'][0] if qid == 'Q2' else answer
                self.assertEqual(actual, dict(zip(CASES[qid][1], CASES[qid][3])))
                self.assertNotIn('size_as_printed', actual)
                self.assertNotIn('ost_files_excluded', actual)
                cert = check(row['claim'], 'Valid'+qid, source, out_dir=root)
                self.assertEqual(cert['status'], 'verified', cert)

    def test_missing_roles_and_foreign_origins_cannot_license_partial_values(self):
        for qid in CASES:
            for variant in ('missing', 'foreign', *(['old_base'] if qid == 'Q2' else [])):
                with self.subTest(qid=qid, variant=variant):
                    result, _, _, _ = self.fixture(qid, variant)
                    self.assertFalse(result['leaves'])
                    self.assertTrue(result['unsupported'])

    def test_wrong_exclusion_name_cannot_license_even_literal_key(self):
        result, _, _, _ = self.fixture('Q50', 'wrong_name')
        self.assertFalse(result['leaves'])
        self.assertTrue(result['unsupported'])

    def test_mixed_subjects_and_wrong_role_kinds_fail_checker(self):
        # A preserves literal unverified proposals; the checker is the subject/type boundary.
        for qid in CASES:
            for variant in ('mixed', 'wrong_kind'):
                with self.subTest(qid=qid, variant=variant):
                    _, row, source, root = self.fixture(qid, variant)
                    cert = check(row['claim'], 'Invalid'+qid+variant, source, out_dir=root)
                    self.assertNotEqual(cert['status'], 'verified', cert)

    def test_stronger_unimplemented_leaves_stay_explicit(self):
        for qid, field in [('Q2', 'size_as_printed'), ('Q50', 'ost_files_excluded')]:
            filename = CASES[qid][0]
            part = json.loads((ROOT/'eval/data_leakage_strict_draft/parts'/filename).read_text())
            q = next(q for q in part['questions'] if q['id'] == qid)
            props = q['answer_schema']['properties']
            if qid == 'Q2': props = props['partitions']['items']['properties']
            self.assertTrue(props[field]['x-claim-requirement']['semantic_types'][0].startswith('needs_'))
