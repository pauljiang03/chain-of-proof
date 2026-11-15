"""Origin constraints inspect actual supporting records, never proposal metadata."""
import unittest
from copy import deepcopy
from checker.facts import Fact
from agent.answer_projection import project_answers, claim_digest, render_projection, catalog
from agent.answer_requirements import inspect, SCOPE_KEY
from tests.test_answer_requirements import Source

ORIGIN = {'image': 'disk.E01', 'exhibit': 'EX1', 'source_snapshot': 'base-volume', 'source_variant': 'primary'}
DIGEST = 'a' * 64


class AnswerScopeRequirements(unittest.TestCase):
    def run_projection(self, origins=None, schema=None, claim=None, digest=DIGEST, candidate_extra=None, strict=True):
        source = Source()
        for fid, origin in (origins or {1: ORIGIN}).items():
            row = source.rows[fid]
            source.rows[fid] = Fact(row.id, row.kind, row.t, row.res, row.obj, row.aux, deepcopy(origin))
        candidate = {'candidate_id': 'C', 'claim': claim or {'programRan': [1]}, **(candidate_extra or {})}
        schema = schema if schema is not None else {'type': 'string', SCOPE_KEY: {'mode': 'source_records', 'origins': [ORIGIN]}}
        contract = {'schema_version': 2, 'case_id': 'case', 'questions': [{'id': 'Q', 'prompt': 'Selected source?', 'answer_schema': schema}]}
        field = 'earlier_recorded_time_us' if 'before' in candidate['claim'] else 'program'
        binding = {'candidate_id': 'C', 'claim_sha256': claim_digest(candidate['claim']), 'question_id': 'Q', 'path': [], 'field': field}
        return project_answers(contract, [candidate], [binding], source, require_evidence_scope=strict, evidence_facts_sha256=digest)

    def test_selected_origin_and_digest_are_frozen(self):
        result = self.run_projection()
        self.assertEqual(result['submission']['answers'][0]['answer'], 'POSTBOX.EXE')
        self.assertEqual(result['projection']['evidence_facts_sha256'], DIGEST)
        self.assertEqual(result['leaves'][0]['scope_checks'][0]['record_origins'], [ORIGIN])
        self.assertEqual(render_projection(result['projection'])['submission'], result['submission'])

    def test_each_qualifier_missing_wrong_or_unknown_refuses_candidate_forgery(self):
        for key in ORIGIN:
            for change in ('missing', 'other', 'unknown'):
                origin = dict(ORIGIN)
                if change == 'missing':
                    del origin[key]
                else:
                    origin[key] = change
                result = self.run_projection({1: origin}, candidate_extra={'provenance': ORIGIN, 'record_origins': [ORIGIN]})
                self.assertEqual(result['unsupported'][0]['reason'], 'claim_records_do_not_meet_public_scope')
                self.assertEqual(result['submission']['answers'][0]['status'], 'unknown')

    def test_vss_and_every_join_support_record_are_checked(self):
        historical = dict(ORIGIN, source_snapshot='vss:copy-1')
        result = self.run_projection({1: ORIGIN, 2: historical}, claim={'before': [1, 2]},
            schema={SCOPE_KEY: {'mode': 'source_records', 'origins': [ORIGIN]}})
        self.assertEqual(result['unsupported'][0]['reason'], 'claim_records_do_not_meet_public_scope')
        self.assertEqual(render_projection(result['projection'], admitted_ids=[])['unsupported'], result['unsupported'])

    def test_source_records_require_trusted_digest_and_optional_expected_match(self):
        self.assertEqual(self.run_projection(digest=None)['unsupported'][0]['reason'], 'evidence_facts_sha256_required')
        schema = {SCOPE_KEY: {'mode': 'source_records', 'origins': [ORIGIN], 'evidence_facts_sha256': 'b' * 64}}
        self.assertEqual(self.run_projection(schema=schema)['unsupported'][0]['reason'], 'evidence_facts_sha256_mismatch')

    def test_explicit_scope_is_enforced_without_policy_and_unscoped_needs_reason(self):
        result = self.run_projection({1: {}}, strict=False)
        self.assertEqual(result['unsupported'][0]['reason'], 'claim_records_do_not_meet_public_scope')
        schema = {SCOPE_KEY: {'mode': 'unscoped_observation', 'meaning': 'Historical observation only.'}}
        self.assertEqual(self.run_projection(schema=schema, digest=None)['submission']['answers'][0]['answer'], 'POSTBOX.EXE')
        schema[SCOPE_KEY]['meaning'] = ''
        self.assertEqual(self.run_projection(schema=schema)['unsupported'][0]['reason'], 'invalid_public_claim_scope_requirement')

    def test_anyof_cannot_drop_or_override_inherited_scope(self):
        scope = {'mode': 'source_records', 'origins': [ORIGIN]}
        schema = {SCOPE_KEY: scope, 'anyOf': [
            {'type': 'string', SCOPE_KEY: {'mode': 'unscoped_observation', 'meaning': 'Narrow observation.'}},
            {'type': 'string'}]}
        self.assertEqual(self.run_projection({1: {}}, schema=schema)['unsupported'][0]['reason'], 'claim_records_do_not_meet_public_scope')
        schema = {'anyOf': [{'type': 'string', SCOPE_KEY: scope}, {'type': 'string'}]}
        self.assertEqual(self.run_projection(schema=schema)['unsupported'][0]['reason'], 'missing_public_claim_scope_requirement')

    def test_preflight_missing_invalid_and_separate_scope_rows(self):
        view = inspect({'type': 'string'}, catalog()['forms'], require_evidence_scope=True)
        self.assertIn('missing_public_claim_scope_requirement', [row['reason'] for row in view['requirements']])
        schema = {SCOPE_KEY: {'mode': 'source_records', 'origins': [dict(ORIGIN, image='*')]}}
        view = inspect(schema, catalog()['forms'], require_evidence_scope=True)
        self.assertIn('invalid_public_claim_scope_requirement', [row['reason'] for row in view['requirements']])
        schema[SCOPE_KEY]['origins'] = [ORIGIN]
        view = inspect(schema, catalog()['forms'], require_evidence_scope=True)
        self.assertEqual(view['requirements'], [])
        self.assertEqual(view['scope_requirements'][0]['status'], 'valid')

    def test_ancestor_scope_applies_to_descendant_leaf_and_no_record_census_refuses(self):
        source = Source()
        row = source.rows[1]
        source.rows[1] = Fact(row.id, row.kind, row.t, row.res, row.obj, row.aux, ORIGIN)
        for claim, path, field, schema, expected in [
                ({'programRan': [1]}, ['observed'], 'program',
                 {'type': 'object', SCOPE_KEY: {'mode': 'source_records', 'origins': [ORIGIN]},
                  'properties': {'observed': {'type': 'string'}}}, None),
                ({'exactly': ['programRun', 1]}, [], 'count',
                 {SCOPE_KEY: {'mode': 'source_records', 'origins': [ORIGIN]}},
                 'claim_scope_supporting_records_missing')]:
            candidate = {'candidate_id': 'C', 'claim': claim}
            contract = {'schema_version': 2, 'case_id': 'case', 'questions': [
                {'id': 'Q', 'prompt': 'Selected source?', 'answer_schema': schema}]}
            binding = {'candidate_id': 'C', 'claim_sha256': claim_digest(claim), 'question_id': 'Q', 'path': path, 'field': field}
            result = project_answers(contract, [candidate], [binding], source,
                                     require_evidence_scope=True, evidence_facts_sha256=DIGEST)
            if expected:
                self.assertEqual(result['unsupported'][0]['reason'], expected)
            else:
                self.assertEqual(result['submission']['answers'][0]['answer'], {'observed': 'POSTBOX.EXE'})

    def test_public_origin_cannot_authorize_unknown_snapshot_or_variant(self):
        for qualifier in ('source_snapshot', 'source_variant'):
            for value in ('unknown', 'UNKNOWN', ' unknown '):
                origin = dict(ORIGIN, **{qualifier: value})
                schema = {SCOPE_KEY: {'mode': 'source_records', 'origins': [origin]}}
                result = self.run_projection({1: origin}, schema=schema)
                self.assertEqual(result['unsupported'][0]['reason'], 'invalid_public_claim_scope_requirement')
                view = inspect(schema, catalog()['forms'], require_evidence_scope=True)
                self.assertIn('invalid_public_claim_scope_requirement', [row['reason'] for row in view['requirements']])

    def test_antivirus_scope_requires_exact_scan_input_origin(self):
        origin = dict(ORIGIN, source_snapshot='examination', source_variant='antivirus',
                      input_source={'source_snapshot': 'base-volume', 'source_variant': 'primary'})
        schema = {SCOPE_KEY: {'mode': 'source_records', 'origins': [origin]}}
        self.assertEqual(self.run_projection({1: origin}, schema=schema)['submission']['answers'][0]['answer'], 'POSTBOX.EXE')
        variants = [None, {}, {'source_snapshot': 'base-volume'},
                    {'source_snapshot': 'vss:copy-1', 'source_variant': 'primary'},
                    {'source_snapshot': 'base-volume', 'source_variant': 'registry-backup:SYSTEM'},
                    {'source_snapshot': 'base-volume', 'source_variant': 'primary', 'extra': 'forged'},
                    {'source_snapshot': 'unknown', 'source_variant': 'primary'}]
        for input_source in variants:
            actual = dict(origin)
            if input_source is None:
                del actual['input_source']
            else:
                actual['input_source'] = input_source
            result = self.run_projection({1: actual}, schema=schema)
            self.assertEqual(result['unsupported'][0]['reason'], 'claim_records_do_not_meet_public_scope')
        for invalid in [None, {}, {'source_snapshot': 'unknown', 'source_variant': 'primary'},
                        {'source_snapshot': 'base-volume', 'source_variant': 'unknown'}]:
            declared = dict(origin)
            if invalid is None:
                del declared['input_source']
            else:
                declared['input_source'] = invalid
            result = self.run_projection({1: declared}, schema={SCOPE_KEY: {'mode': 'source_records', 'origins': [declared]}})
            self.assertEqual(result['unsupported'][0]['reason'], 'invalid_public_claim_scope_requirement')
        # Input source is meaningful only for an examination, not a base row.
        declared = dict(ORIGIN, input_source=origin['input_source'])
        self.assertEqual(self.run_projection(schema={SCOPE_KEY: {'mode': 'source_records', 'origins': [declared]}})
                         ['unsupported'][0]['reason'], 'invalid_public_claim_scope_requirement')

    def test_unavailable_scope_is_valid_visible_and_always_refuses_binding(self):
        schema = {SCOPE_KEY: {'mode': 'unavailable', 'meaning': 'The requested VSS copy ID has not been selected.'}}
        view = inspect(schema, catalog()['forms'], require_evidence_scope=True)
        self.assertEqual(view['requirements'], [])
        self.assertEqual(view['scope_requirements'][0]['status'], 'unavailable')
        for strict in (True, False):
            result = self.run_projection(schema=schema, digest=None, strict=strict)
            self.assertEqual(result['submission']['answers'][0]['status'], 'unknown')
            self.assertEqual(result['unsupported'][0]['reason'], 'public_claim_scope_unavailable')
            self.assertEqual(render_projection(result['projection'], admitted_ids=[])['unsupported'], result['unsupported'])
        schema[SCOPE_KEY]['meaning'] = ''
        self.assertEqual(self.run_projection(schema=schema)['unsupported'][0]['reason'], 'invalid_public_claim_scope_requirement')

    def test_canonical_special_origins_match_only_the_exact_strings(self):
        for snapshot, variant in [('base-volume', 'unallocated-recovery'),
                                  ('optical-image', 'primary'), ('optical-image', 'udf-recovered-entry:2'),
                                  ('optical-image', 'udf-descriptor:1'), ('evidence-image', 'logical-image'),
                                  ('evidence-image', 'acquisition-container')]:
            origin = dict(ORIGIN, source_snapshot=snapshot, source_variant=variant)
            schema = {SCOPE_KEY: {'mode': 'source_records', 'origins': [origin]}}
            self.assertEqual(self.run_projection({1: origin}, schema=schema)['submission']['answers'][0]['answer'], 'POSTBOX.EXE')
            self.assertEqual(self.run_projection({1: dict(origin, source_variant=variant + '-alias')}, schema=schema)
                             ['unsupported'][0]['reason'], 'claim_records_do_not_meet_public_scope')

    def test_unavailable_gap_cannot_be_overridden_by_anyof_or_parent_scope(self):
        gap = {'mode': 'unavailable', 'meaning': 'Selected snapshot ID unavailable.'}
        schema = {SCOPE_KEY: {'mode': 'source_records', 'origins': [ORIGIN]}, 'anyOf': [
            {'type': 'string', SCOPE_KEY: gap}, {'type': 'string'}]}
        result = self.run_projection(schema=schema, digest=None)
        self.assertEqual(result['unsupported'][0]['reason'], 'public_claim_scope_unavailable')

    def test_closed_alternative_exclusive_paths_keep_only_applicable_scopes(self):
        from agent.answer_requirements import applicable_scopes
        gap = {'mode': 'unavailable', 'meaning': 'No selected action source.'}
        schema = {'type': 'object', SCOPE_KEY: gap, 'properties': {'actions': {
            'type': 'array', 'items': {'anyOf': [
                {'type': 'object', 'additionalProperties': False, 'properties': {'method': {'type': 'string'}}},
                {'type': 'object', 'additionalProperties': False, 'properties': {'file_groups': {'type': 'string'}}},
                {'type': 'object', 'additionalProperties': False, 'properties': {'purpose': {'type': 'string'}}}]}}}}
        view = inspect(schema, catalog()['forms'], require_evidence_scope=True)
        self.assertEqual(view['requirements'], [])
        for field in ('method', 'file_groups', 'purpose'):
            self.assertEqual(applicable_scopes(schema, ['actions', 0, field], require_evidence_scope=True), [gap])
        with self.assertRaisesRegex(ValueError, 'field_not_in_public_schema'):
            applicable_scopes(schema, ['actions', 0, 'not_present'], require_evidence_scope=True)
        # A declaration in a different closed branch cannot supply a missing scope.
        schema = {'anyOf': [
            {'type': 'object', 'additionalProperties': False, SCOPE_KEY: gap,
             'properties': {'method': {'type': 'string'}}},
            {'type': 'object', 'additionalProperties': False, 'properties': {'purpose': {'type': 'string'}}}]}
        with self.assertRaisesRegex(ValueError, 'missing_public_claim_scope_requirement'):
            applicable_scopes(schema, ['purpose'], require_evidence_scope=True)
