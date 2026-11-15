"""Public typed answers use kernel-checked tuples, exact roles and source families."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from agent.answer_projection import claim_digest, project_answers
from checker.catalog import ROLES
from checker.check import check
from checker.facts import JsonFacts
from extractor.attributes import emit_attribute
from extractor.store import Evidence
from verifier.verify import verify

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = dict(image='pc.E01', exhibit='PC', source_snapshot='base-volume', source_variant='primary')


class SupportedPublicTuples(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.public = json.loads((ROOT / 'tests/fixtures/contracts/data-leakage/questions.json').read_text())
        self.ev = Evidence()
        self.identities = {}
        self.groups = {
            'os': [('os.product_name', 'Fixture OS'), ('os.version', '6.1'),
                   ('os.build_number', 12345), ('os.registered_owner', 'Fixture owner'),
                   ('os.system_root', r'C:\FixtureWindows'), ('os.install_time', '2001-02-03T04:05:06Z')],
            'ua': [('app.execution.path', r'C:\Fixture\observed.exe'),
                   ('app.execution.recorded_time', '2002-03-04T05:06:07Z'),
                   ('app.execution.run_count', 7), ('app.execution.source_type', 'UserAssist'),
                   ('app.execution.time_meaning', 'execution')],
            'security': [('app.execution.path', r'C:\Fixture\security.exe'),
                         ('app.execution.recorded_time', '2003-04-05T06:07:08Z'),
                         ('app.execution.source_type', 'Security process creation')],
            'browser': [('browser.history.browser', 'Chrome'),
                        ('browser.history.path', r'C:\Fixture\History')],
            'mail': [('mail.store.path', r'C:\Fixture\fixture.ost')],
            'thumb': [('thumbcache.container.path', r'C:\Fixture\thumbcache_256.db')],
            'sticky': [('sticky_notes.container.path', r'C:\Fixture\StickyNotes.snt')],
        }
        for group, values in self.groups.items():
            for role, value in values:
                self.add(group, role, value)
        self.add('ua', 'app.execution.raw_run_count', 12)
        for group in ('mail', 'thumb', 'sticky'):
            self.add('generic_' + group, 'source.path', self.groups[group][0][1])
        self.add('generic_browser', 'source.path', self.groups['browser'][1][1])
        self.path = self.root / 'facts.json'
        self.ev.write_json(self.path, {})
        self.source = JsonFacts(self.path)
        self.digest = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.sequence = 0

    def add(self, group, role, value):
        self.identities[group, role] = emit_attribute(
            self.ev, 'synthetic:' + group, role, value, 9_000_000_000,
            artifact='synthetic reviewed source ' + group, **ORIGIN)

    def entry(self, group, role):
        identity = self.identities[group, role]
        rows = {f.kind: f.id for f in self.source.all() if self.source.string(f.obj) == identity}
        spec = ROLES[role]
        return [rows['attributeSubject'], rows[spec.kind], rows[spec.value_kind], role]

    def candidate(self, group, roles=None, claim=None):
        self.sequence += 1
        if claim is None:
            roles = roles or [role for role, _ in self.groups[group]]
            entries = [self.entry(group, role) for role in roles]
            claim = {'attributeTuple': entries} if len(entries) > 1 else {'attributeRecorded': entries[0]}
        return {'candidate_id': 'Fixture' + str(self.sequence), 'claim': claim}

    def certify(self, candidate):
        certificate = check(candidate['claim'], candidate['candidate_id'], self.source, out_dir=self.root)
        self.assertEqual(certificate['status'], 'verified', certificate)
        self.assertEqual(certificate['trust_tier'], 'kernel')
        self.assertEqual(certificate['axioms'], [])
        self.assertEqual(verify(certificate, self.source), [], 'independent replay must pass')
        return certificate

    def bind(self, candidate, qid, path, field, part=0):
        return dict(candidate_id=candidate['candidate_id'], claim_sha256=claim_digest(candidate['claim']),
                    question_id=qid, path=path, field=field, part=part)

    def project(self, candidate, bindings, certify=True):
        if certify:
            self.certify(candidate)
        return project_answers(self.public, [candidate], bindings, self.source,
                               admitted_ids=[candidate['candidate_id']], authority='independently_replayed',
                               require_claim_requirements=True, require_evidence_scope=True,
                               evidence_facts_sha256=self.digest)

    def answer(self, result, qid):
        return next(a for a in result['submission']['answers'] if a['question_id'] == qid)

    def test_q3_six_os_fields_are_one_kernel_tuple_with_native_build(self):
        candidate = self.candidate('os')
        fields = ['os_name', 'version', 'build_number', 'registered_owner', 'system_root', 'installed_at']
        bindings = [self.bind(candidate, 'Q3', [field], 'value_' + str(i)) for i, field in enumerate(fields)]
        result = self.project(candidate, bindings)
        self.assertFalse(result['unsupported'])
        self.assertEqual(self.answer(result, 'Q3')['answer'],
                         dict(zip(fields, [value for _, value in self.groups['os']])))
        self.assertIs(type(self.answer(result, 'Q3')['answer']['build_number']), int)
        self.assertEqual(result['projection']['evidence_facts_sha256'], self.digest)
        self.assertTrue(all(len(leaf['record_ids']) == 18 for leaf in result['leaves']))

    def test_q11_five_userassist_fields_preserve_artifact_time_and_interpreted_count(self):
        candidate = self.candidate('ua')
        fields = ['path_or_application_id', 'timestamp', 'execution_count', 'source', 'time_meaning']
        bindings = [self.bind(candidate, 'Q11', ['records', 0, field], 'value_' + str(i))
                    for i, field in enumerate(fields)]
        result = self.project(candidate, bindings)
        self.assertFalse(result['unsupported'])
        record = self.answer(result, 'Q11')['answer']['records'][0]
        self.assertEqual(record, dict(zip(fields, [value for _, value in self.groups['ua']])))
        self.assertIs(type(record['execution_count']), int)
        self.assertNotEqual(record['timestamp'], '1970-01-01T02:30:00Z')  # examination time
        for leaf in result['leaves']:
            checks = leaf['meaning_checks'][0]['condition_checks']
            self.assertEqual(checks[0]['offered_value'], 'UserAssist')
            self.assertEqual(checks[0]['status'], 'compatible')

    def test_q11_partial_path_and_source_tuple_does_not_invent_timestamp_or_null(self):
        candidate = self.candidate('ua', ['app.execution.path', 'app.execution.source_type'])
        result = self.project(candidate, [self.bind(candidate, 'Q11', ['records', 0, 'path_or_application_id'], 'value_0'),
                                          self.bind(candidate, 'Q11', ['records', 0, 'source'], 'value_1')])
        self.assertFalse(result['unsupported'])
        self.assertEqual(self.answer(result, 'Q11')['answer'],
                         {'records': [{'path_or_application_id': self.groups['ua'][0][1], 'source': 'UserAssist'}]})

    def test_q11_security_family_refuses_path_and_time_even_without_source_column(self):
        candidate = self.candidate('security')
        for include_source in (False, True):
            bindings = [self.bind(candidate, 'Q11', ['records', 0, 'path_or_application_id'], 'value_0'),
                        self.bind(candidate, 'Q11', ['records', 0, 'timestamp'], 'value_1')]
            if include_source:
                bindings.append(self.bind(candidate, 'Q11', ['records', 0, 'source'], 'value_2'))
            result = self.project(candidate, bindings)
            self.assertEqual(self.answer(result, 'Q11')['status'], 'unknown')
            self.assertEqual(result['leaves'], [])
            self.assertEqual(len(result['unsupported']), len(bindings))
            for row in result['unsupported']:
                if row['binding']['path'][-1] == 'source':
                    self.assertEqual(row['reason'], 'value_not_in_public_schema_enum')
                else:
                    checks = row['meaning_checks'][0]['condition_checks']
                    self.assertEqual(checks[0]['status'], 'incompatible')
                    self.assertEqual(checks[0]['offered_value'], 'Security process creation')

    def test_q11_source_in_another_both_part_cannot_authorize_path_part(self):
        path_time = {'attributeTuple': [self.entry('ua', 'app.execution.path'),
                                       self.entry('ua', 'app.execution.recorded_time')]}
        source = {'attributeRecorded': self.entry('ua', 'app.execution.source_type')}
        candidate = self.candidate('ua', claim={'both': [path_time, source]})
        result = self.project(candidate, [self.bind(candidate, 'Q11', ['records', 0, 'path_or_application_id'], 'value_0'),
                                          self.bind(candidate, 'Q11', ['records', 0, 'timestamp'], 'value_1')])
        self.assertEqual(self.answer(result, 'Q11')['status'], 'unknown')
        self.assertTrue(all(r['meaning_checks'][0]['condition_checks'][0]['status'] == 'missing'
                            for r in result['unsupported']))

    def test_q11_duplicate_source_fields_cannot_satisfy_exactly_one_match(self):
        entries = [self.entry('ua', 'app.execution.path'), self.entry('ua', 'app.execution.source_type'),
                   self.entry('ua', 'app.execution.source_type')]
        candidate = self.candidate('ua', claim={'attributeTuple': entries})
        rejected = check(candidate['claim'], candidate['candidate_id'], self.source, out_dir=self.root)
        self.assertNotEqual(rejected['status'], 'verified')
        # The unchecked literal projection must also refuse ambiguous source
        # matches rather than selecting the first one, before kernel filtering.
        result = project_answers(self.public, [candidate],
                                 [self.bind(candidate, 'Q11', ['records', 0, 'path_or_application_id'], 'value_0')],
                                 self.source, require_claim_requirements=True, require_evidence_scope=True,
                                 evidence_facts_sha256=self.digest)
        self.assertEqual(result['leaves'], [])
        self.assertEqual(result['unsupported'][0]['meaning_checks'][0]['condition_checks'][0]['status'], 'ambiguous')

    def test_q11_raw_counter_and_examination_time_cannot_substitute(self):
        candidate = self.candidate('ua', ['app.execution.path', 'app.execution.raw_run_count',
                                          'app.execution.source_type'])
        result = self.project(candidate, [self.bind(candidate, 'Q11', ['records', 0, 'execution_count'], 'value_1'),
                                          self.bind(candidate, 'Q11', ['records', 0, 'timestamp'], 'examined_at_us')])
        self.assertEqual(self.answer(result, 'Q11')['status'], 'unknown')
        self.assertEqual(result['leaves'], [])
        self.assertEqual(result['unsupported'][0]['reason'], 'claim_role_does_not_meet_public_requirement')
        self.assertTrue(all(row['reason'] in ('claim_role_does_not_meet_public_requirement',
                                               'value_type_does_not_match_public_schema',
                                               'field_not_supported_or_cited_record_missing')
                            for row in result['unsupported']))

    def test_q14_validated_history_browser_and_path_share_one_tuple(self):
        candidate = self.candidate('browser')
        result = self.project(candidate, [self.bind(candidate, 'Q14', ['artifacts', 0, 'browser'], 'value_0'),
                                          self.bind(candidate, 'Q14', ['artifacts', 0, 'path'], 'value_1')])
        self.assertFalse(result['unsupported'])
        self.assertEqual(self.answer(result, 'Q14')['answer'],
                         {'artifacts': [{'browser': 'Chrome', 'path': self.groups['browser'][1][1]}]})

    def test_validated_container_roles_accept_but_verified_generic_paths_refuse(self):
        for group, qid, path in [('mail', 'Q19', ['path_as_printed']),
                                 ('thumb', 'Q38', ['paths', 0]), ('sticky', 'Q40', ['path'])]:
            with self.subTest(question=qid):
                candidate = self.candidate(group)
                result = self.project(candidate, [self.bind(candidate, qid, path, 'value')])
                self.assertFalse(result['unsupported'])
                self.assertEqual(len(result['leaves']), 1)
                self.assertEqual(result['leaves'][0]['value'], self.groups[group][0][1])
                generic = self.candidate('generic_' + group, ['source.path'])
                refused = self.project(generic, [self.bind(generic, qid, path, 'value')])
                self.assertEqual(self.answer(refused, qid)['status'], 'unknown')
                self.assertEqual(refused['unsupported'][0]['reason'], 'claim_role_does_not_meet_public_requirement')
        generic = self.candidate('generic_browser', ['source.path'])
        refused = self.project(generic, [self.bind(generic, 'Q14', ['artifacts', 0, 'path'], 'value')])
        self.assertEqual(self.answer(refused, 'Q14')['status'], 'unknown')
        self.assertEqual(refused['unsupported'][0]['reason'], 'claim_role_does_not_meet_public_requirement')


if __name__ == '__main__':
    unittest.main()
