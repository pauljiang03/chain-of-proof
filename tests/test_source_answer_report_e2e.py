"""Byte-to-report checks on a tiny UTF-8 client log, using the real cloud reader and Lean (no model)."""
from copy import deepcopy
import hashlib
import html
import json
from pathlib import Path
import tempfile
import unittest

from agent.answer_projection import claim_digest, project_answers
from agent.answer_store import project_bundle, public_profile, report_projection
from app import brief, narrative
from app.report import render_html, report_options
from checker.catalog import ROLES
from checker.check import check
from checker.facts import JsonFacts
from checker.report import render as render_markdown
from extractor.cloud_attributes import extract_paths
from extractor.store import Evidence
from verifier.verify import verify


# The header clock is UTC-04:30, while the server fields are Unix seconds.
# Their three distinct meanings must survive extraction and every display.
RAW = (
    b'2020-07-01 12:00:00,005 -0430 INFO pid=12 3:Worker common.sync_app:42 Config:\r\n'
    b'2020-07-01 12:00:01,005 -0430 INFO pid=12 3:Worker common.cloud.cloud_watcher:42 '
    b'Got: [CloudEntry(doc_id=DOC_A,filename=literal.txt,modified=1593619100,created=1593619000,'
    b'acl_role=owner,doc_type=DocType.BLOB)]\r\n'
    b'2020-07-01 12:00:02,005 -0430 INFO pid=12 3:Worker common.cloud.cloud_watcher:42 '
    b'Built: [WorkerDeleteCloudEvent(doc_id=DOC_A, server_mod_time=1593619300, version=None)]\r\n'
    b'2020-07-01 12:00:03,005 -0430 INFO pid=12 3:Worker common.service.user:42 '
    b'Initializing User instance with new credentials. fixture@example.invalid\r\n'
)
EXAMINED = 1_800_000_000_000_000
CONTAINER = ('cloud.container.service', 'cloud.container.type', 'cloud.container.path')
PREFIX = 'cloud.google_drive.'


class SourceAnswerReportE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        public = json.loads((Path(__file__).resolve().parent / 'fixtures/contracts/data-leakage/questions.json').read_text())
        cls.public = dict(public, questions=[q for q in public['questions'] if q['id'] in ('Q29', 'Q30', 'Q31')])
        cls.origin = next(q for q in cls.public['questions'] if q['id'] == 'Q29')['answer_schema']['x-claim-scope']['origins'][0]

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ev = Evidence()
        self.sequence = 0
        self.log = self.root / 'arbitrary-client-name.bin'
        self.extract(self.log, RAW)

    def extract(self, path, raw, origin=None):
        path.write_bytes(raw)
        extract_paths(self.ev, [path], {'examined_at': EXAMINED, 'common': origin or self.origin})
        self.facts = self.root / 'facts.json'
        self.ev.write_json(self.facts, {})
        self.source = JsonFacts(self.facts)
        self.digest = hashlib.sha256(self.facts.read_bytes()).hexdigest()

    def entry(self, role, *, path=None, observation=None):
        values = [fact for fact in self.source.all() if fact.kind == ROLES[role].value_kind
                  and fact.prov.get('attribute_role') == role
                  and (path is None or fact.prov['source_path'] == str(path).replace('/', '\\'))
                  and (observation is None or fact.prov.get('observation_kind') == observation)]
        self.assertEqual(len(values), 1, (role, path, observation, values))
        value = values[0]
        triple = {fact.kind: fact.id for fact in self.source.all() if fact.obj == value.obj}
        return [triple['attributeSubject'], triple[ROLES[role].kind], value.id, role]

    def candidate(self, roles, *, path=None, observation=None):
        self.sequence += 1
        entries = [self.entry(role, path=path, observation=observation) for role in roles]
        return {'candidate_id': 'E2E' + str(self.sequence),
                'claim': {'attributeTuple': entries} if len(entries) > 1 else {'attributeRecorded': entries[0]}}

    def certify(self, candidate, accepted=True):
        cert = check(candidate['claim'], candidate['candidate_id'], self.source, out_dir=self.root)
        self.assertEqual(cert['status'] == 'verified', accepted, cert)
        if accepted:
            self.assertEqual((cert['trust_tier'], cert['axioms']), ('kernel', []))
            self.assertEqual(verify(cert, self.source), [])
        return cert

    def bind(self, candidate, qid, path, field):
        return {'candidate_id': candidate['candidate_id'], 'claim_sha256': claim_digest(candidate['claim']),
                'question_id': qid, 'path': path, 'field': field, 'part': 0}

    def project(self, candidate, bindings, admitted=True):
        return project_answers(self.public, [candidate], bindings, self.source,
                               admitted_ids=[candidate['candidate_id']] if admitted else [],
                               require_claim_requirements=True, require_evidence_scope=True,
                               evidence_facts_sha256=self.digest)

    def bundle(self, cert, bindings):
        run = {'case': {'name': 'Synthetic source-to-report control', 'facts_sha256': self.digest},
               'findings': [cert], 'rejections': [], 'conclusions': [],
               'stats': {'verified': 1, 'rejected': 0, 'proposals': 1},
               'investigation': dict(self.public, facts_sha256=self.digest),
               'answer_bindings': {'schema_version': 1, 'case_id': self.public['case_id'],
                                   'facts_sha256': self.digest, 'bindings': bindings},
               'run_manifest': {'inputs': {'facts': {'sha256': self.digest}}}}
        run['answer_projection'] = project_bundle(run, public_profile(run['investigation']))
        self.assertIsNone(report_projection(run)[1])
        return run

    def test_known_bytes_reach_kernel_public_fields_and_both_reports(self):
        self.assertEqual(self.ev.problems, [])
        candidate = self.candidate(CONTAINER)
        cert = self.certify(candidate)
        bindings = [self.bind(candidate, 'Q29', ['traces', 0, field], 'value_' + str(i))
                    for i, field in enumerate(('service', 'type', 'path'))]
        result = self.project(candidate, bindings)
        self.assertEqual(result['unsupported'], [])
        expected = {'service': 'Google Drive', 'type': 'Google Drive sync log',
                    'path': str(self.log).replace('/', '\\')}
        self.assertEqual(result['submission']['answers'][0]['answer'], {'traces': [expected]})
        self.assertEqual(len(result['leaves']), 3)
        self.assertTrue(all(len(leaf['record_ids']) == 9 for leaf in result['leaves']))
        run = self.bundle(cert, bindings)
        for rendered in (html.unescape(render_html(run)), render_markdown(run)):
            self.assertIn('Structured answers from claim fields', rendered)
            self.assertIn('Google Drive sync log', rendered)
            self.assertIn('completeness', rendered)
        full = render_html(run)
        self.assertIn(html.escape(cert['english']), full)
        info = brief.build(run)
        self.assertEqual((info['counts']['records'], info['counts']['dated']), (9, 0))
        self.assertEqual(info['days'], [])
        self.assertIsNone(info['range'])
        self.assertEqual(narrative.build(run)['points'], [])
        short = render_html(run, report_options(brief=True, sections=[]))
        self.assertNotIn('<h3>Timeline</h3>', short)
        self.assertNotIn('uploaded', short)

    def test_same_file_name_in_other_container_cannot_supply_tuple_identity(self):
        other = self.root / 'other-client.bin'
        self.extract(other, RAW)
        candidate = self.candidate(CONTAINER, path=self.log)
        candidate['claim']['attributeTuple'][0] = self.entry(CONTAINER[0], path=other)
        cert = self.certify(candidate, accepted=False)
        self.assertNotIn('cited_facts', cert)
        bindings = [self.bind(candidate, 'Q29', ['traces', 0, 'path'], 'value_2')]
        result = self.project(candidate, bindings, admitted=False)
        self.assertEqual(result['leaves'], [])
        self.assertEqual(result['submission']['answers'][0]['status'], 'unknown')

    def test_valid_foreign_snapshot_proof_cannot_become_selected_case_answer(self):
        other = self.root / 'snapshot-client.bin'
        self.extract(other, RAW, dict(self.origin, source_snapshot='vss:fixture-copy'))
        candidate = self.candidate(CONTAINER, path=other)
        self.certify(candidate)
        bindings = [self.bind(candidate, 'Q29', ['traces', 0, 'path'], 'value_2')]
        result = self.project(candidate, bindings)
        self.assertEqual(result['leaves'], [])
        self.assertEqual(result['unsupported'][0]['reason'], 'claim_records_do_not_meet_public_scope')

    def test_credentials_timestamp_is_not_exam_time_or_logon(self):
        candidate = self.candidate((PREFIX + 'credentials_account', PREFIX + 'credentials_used_at'))
        cert = self.certify(candidate)
        bindings = [self.bind(candidate, 'Q31', ['account'], 'value_0'),
                    self.bind(candidate, 'Q31', ['logon_time'], 'value_1')]
        result = self.project(candidate, bindings)
        answer = next(row for row in result['submission']['answers'] if row['question_id'] == 'Q31')
        self.assertEqual(answer['answer'], {'account': 'fixture@example.invalid'})
        self.assertEqual(len(result['unsupported']), 1)
        self.assertIn('2020-07-01T16:30:03.005000Z', cert['english'])
        self.assertTrue(all(row['t'] == EXAMINED for row in cert['cited_facts']))
        self.assertTrue(all(row['prov']['timestamp_semantics'] == 'examination_observation' for row in cert['cited_facts']))
        run = self.bundle(cert, bindings)
        structured = html.unescape(render_html(run)).split('id="structured-answers"', 1)[1].split('</section>', 1)[0]
        self.assertNotIn('"logon_time":', structured.split('Field links and omitted or conflicting bindings')[0])
        self.assertEqual(brief.build(run)['counts']['dated'], 0)

    def test_related_server_times_do_not_establish_deletion_event_or_original_filename(self):
        roles = tuple(PREFIX + name for name in ('document_id', 'file_name', 'server_modified_at',
                                                'deletion_record_server_modified_at'))
        candidate = self.candidate(roles, observation='deleted_document')
        cert = self.certify(candidate)
        value_rows = [row for row in cert['cited_facts'] if row['kind'] == 'attributeTextValue']
        self.assertEqual({row['prov']['container_sha256'] for row in value_rows}, {hashlib.sha256(RAW).hexdigest()})
        for row in value_rows:
            locator = row['prov']['locator']
            raw_line = RAW[locator['byte_offset']:locator['byte_offset'] + locator['byte_length']]
            self.assertEqual(hashlib.sha256(raw_line).hexdigest(), locator['line_sha256'])
        self.assertIn('2020-07-01T15:58:20.000000Z', cert['english'])
        self.assertIn('2020-07-01T16:01:40.000000Z', cert['english'])
        bindings = [self.bind(candidate, 'Q30', ['files', 0, name], field)
                    for name, field in (('filename', 'value_1'), ('modified_at', 'value_2'), ('deleted_at', 'value_3'))]
        result = self.project(candidate, bindings)
        self.assertEqual(result['leaves'], [])
        self.assertEqual(len(result['unsupported']), 3)
        self.assertEqual(next(row for row in result['submission']['answers'] if row['question_id'] == 'Q30')['status'], 'unknown')

    def test_changed_source_record_breaks_replay_and_display_binding(self):
        candidate = self.candidate(CONTAINER)
        cert = self.certify(candidate)
        bindings = [self.bind(candidate, 'Q29', ['traces', 0, 'path'], 'value_2')]
        run = self.bundle(cert, bindings)
        changed = deepcopy(cert)
        changed['cited_facts'][0]['prov']['source_snapshot'] = 'vss:substituted'
        self.assertTrue(verify(changed, self.source))
        run['findings'] = [changed]
        self.assertIsNotNone(report_projection(run)[1])
        rendered = render_html(run)
        self.assertIn('does not match its claim bindings', rendered)


if __name__ == '__main__':
    unittest.main()
