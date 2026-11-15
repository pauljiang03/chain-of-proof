"""Kernel-valid recovered mail observations never acquire primary/deletion meaning."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from agent.answer_projection import claim_digest, project_answers
from agent.answer_requirements import check as check_requirement
from checker.catalog import ROLES
from checker.check import check
from checker.facts import JsonFacts
from extractor.attributes import emit_attribute
from extractor.store import Evidence
from verifier.verify import verify

ROOT = Path(__file__).resolve().parents[1]
BASE = dict(image='pc.E01', exhibit='PC', source_snapshot='base-volume')
TEXT = ('Synthetic retained subject', 'Synthetic retained body\nSecond fixture line.')
RECOVERED_ROLES = ('mail.recovered.subject_unicode', 'mail.recovered.body_unicode')
PRIMARY_ROLES = ('mail.message.subject_unicode', 'mail.message.body_unicode')


class RecoveredAnswerScope(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        ev, identities = Evidence(), {}
        for variant, roles in [('primary', PRIMARY_ROLES), ('parser-recovery', RECOVERED_ROLES)]:
            for role, value in zip(roles, TEXT):
                identities[variant, role] = emit_attribute(
                    ev, 'synthetic-message:' + variant, role, value, 1000000,
                    artifact='synthetic parser message', source_variant=variant, **BASE)
        cls.path = cls.root / 'facts.json'
        ev.write_json(cls.path, {})
        cls.source = JsonFacts(cls.path)
        cls.digest = hashlib.sha256(cls.path.read_bytes()).hexdigest()
        cls.certificates = {}
        for variant, roles in [('primary', PRIMARY_ROLES), ('parser-recovery', RECOVERED_ROLES)]:
            entries = []
            for role in roles:
                identity = identities[variant, role]
                rows = {f.kind: f.id for f in cls.source.all() if cls.source.string(f.obj) == identity}
                spec = ROLES[role]
                entries.append([rows['attributeSubject'], rows[spec.kind], rows[spec.value_kind], role])
            certificate = check({'attributeTuple': entries}, 'Primary' if variant == 'primary' else 'Recovered',
                                cls.source, out_dir=cls.root)
            if certificate['status'] != 'verified' or certificate['trust_tier'] != 'kernel':
                raise AssertionError(certificate)
            if certificate['axioms'] or verify(certificate, cls.source):
                raise AssertionError('Synthetic narrow-mail certificate failed independent replay')
            cls.certificates[variant] = certificate

    def contract(self, variant, roles):
        return {'schema_version': 2, 'case_id': 'synthetic-mail-origin', 'questions': [{
            'id': 'Q', 'prompt': 'Retained source text under this exact declared origin.',
            'answer_schema': {'type': 'object', 'x-claim-row': {'mode': 'same_claim_part'},
                'x-claim-scope': {'mode': 'source_records', 'origins': [dict(BASE, source_variant=variant)]},
                'properties': {name: {'type': 'string', 'x-claim-requirement': {
                    'semantic_types': [ROLES[role].semantic_type],
                    'selectors': [{'form': 'attributeTuple', 'field': 'value_' + str(i)}],
                    'meaning': ROLES[role].meaning,
                    'evidence_needed': 'Exact typed source observation; source variant checked separately.'}}
                    for i, (name, role) in enumerate(zip(('subject', 'body'), roles))}}}]}

    def project(self, public, variant='parser-recovery', targets=None):
        cert = self.certificates[variant]
        candidate = dict(candidate_id=cert['finding_id'], claim=deepcopy(cert['claim']))
        targets = targets or [('Q', ['subject'], 'value_0'), ('Q', ['body'], 'value_1')]
        bindings = [dict(candidate_id=candidate['candidate_id'], claim_sha256=claim_digest(candidate['claim']),
                         question_id=qid, path=path, field=field) for qid, path, field in targets]
        return project_answers(public, [candidate], bindings, self.source,
                               admitted_ids=[candidate['candidate_id']], authority='independently_replayed',
                               require_claim_requirements=True, require_evidence_scope=True,
                               evidence_facts_sha256=self.digest)

    def test_exact_primary_and_parser_recovery_scopes_each_preserve_literal_values(self):
        for variant, roles in [('primary', PRIMARY_ROLES), ('parser-recovery', RECOVERED_ROLES)]:
            with self.subTest(variant=variant):
                result = self.project(self.contract(variant, roles), variant)
                self.assertFalse(result['unsupported'])
                self.assertEqual(result['submission']['answers'][0]['answer'], dict(zip(('subject', 'body'), TEXT)))
                self.assertEqual(result['projection']['evidence_facts_sha256'], self.digest)
                for leaf in result['leaves']:
                    self.assertTrue(all(origin == dict(BASE, source_variant=variant)
                                        for origin in leaf['scope_checks'][0]['record_origins']))

    def test_same_image_exhibit_and_value_cannot_replace_primary_origin(self):
        # Isolate origin from role compatibility: the exact recovered roles are
        # declared, but primary admission still cannot admit parser-recovery.
        public = self.contract('primary', RECOVERED_ROLES)
        result = self.project(public)
        self.assertEqual(result['leaves'], [])
        self.assertEqual(result['submission']['answers'][0]['status'], 'unknown')
        self.assertEqual([row['reason'] for row in result['unsupported']],
                         ['claim_records_do_not_meet_public_scope'] * 2)
        primary = self.project(self.contract('primary', PRIMARY_ROLES), 'primary')
        self.assertEqual(primary['submission']['answers'][0]['answer'], dict(zip(('subject', 'body'), TEXT)))
        for rejected in result['unsupported']:
            for origin in rejected['scope_checks'][0]['record_origins']:
                self.assertEqual({key: origin[key] for key in BASE}, BASE)
                self.assertEqual(origin['source_variant'], 'parser-recovery')

    def test_actual_public_mail_questions_refuse_recovery_as_primary(self):
        public = json.loads((ROOT / 'eval/data_leakage_strict_draft/questions.json').read_text())
        targets = [('Q21', ['messages', 0, 'subject'], 'value_0'),
                   ('Q21', ['messages', 0, 'body'], 'value_1'),
                   ('Q45', ['messages', 0, 'subject'], 'value_0'),
                   ('Q45', ['messages', 0, 'body'], 'value_1'),
                   ('Q52', ['deleted_mail_subjects', 0], 'value_0')]
        result = self.project(public, targets=targets)
        self.assertEqual(result['leaves'], [])
        self.assertEqual(len(result['unsupported']), len(targets))
        self.assertTrue(all(row['reason'] == 'claim_records_do_not_meet_public_scope'
                            for row in result['unsupported']))
        self.assertEqual(verify(self.certificates['parser-recovery'], self.source), [])

    def test_recovered_roles_fail_deleted_and_purged_meaning_even_when_origin_matches(self):
        public = self.contract('parser-recovery', RECOVERED_ROLES)
        schema = public['questions'][0]['answer_schema']
        original = json.loads((ROOT / 'eval/data_leakage_strict_draft/questions.json').read_text())
        q52 = next(q for q in original['questions'] if q['id'] == 'Q52')
        # Reuse the actual stronger public deletion requirement, while making
        # source origin intentionally compatible to test the separate boundary.
        deleted = deepcopy(q52['answer_schema']['properties']['deleted_mail_subjects']['items']['x-claim-requirement'])
        schema['properties']['subject']['x-claim-requirement'] = deleted
        schema['properties']['body']['x-claim-requirement'] = {
            'semantic_types': ['needs_explicitly_proven_purged_message_body'],
            'meaning': 'Body of a message established as purged by an approved source-state rule.',
            'evidence_needed': 'Explicit purge-state evidence joined to this message; parser recovery alone is insufficient.'}
        result = self.project(public)
        self.assertEqual(result['leaves'], [])
        self.assertEqual([row['reason'] for row in result['unsupported']],
                         ['claim_role_does_not_meet_public_requirement'] * 2)
        for role in RECOVERED_ROLES:
            result = check_requirement(deleted, 'attributeTuple', 'value_0', ROLES[role].semantic_type)
            self.assertEqual(result['status'], 'incompatible')
        cert = self.certificates['parser-recovery']
        self.assertEqual(verify(cert, self.source), [])
        self.assertTrue(all('not proof' in ROLES[role].meaning for role in RECOVERED_ROLES))


if __name__ == '__main__':
    unittest.main()
