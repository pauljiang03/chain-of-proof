"""Deterministic, synthetic-only public-role receipts; run directly, not a test suite.

This demonstrates a superseded draft-like annotation weakness and checks that
reviewed requirements withhold the corresponding stronger answers. It does not
measure case accuracy, entailment, parser correctness or completeness.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from agent.answer_projection import claim_digest, prepare_projection, render_projection
from checker.check import check
from checker.facts import Fact, FactSource
from verifier.verify import verify


class SyntheticSource(FactSource):
    def __init__(self):
        self.strings = {1: 'SYNTHETIC-COPY-A', 2: 'SYNTHETIC-COPY-B',
                        3: 'SYNTHETIC-VOLUME', 4: 'SYNTHETIC-APP',
                        5: r'C:\Synthetic\never_proven_run.exe'}
        self.rows = {
            1: Fact(1, 'shadowCopy', 1_000_000, 1, 1, 3,
                    {'artifact': 'synthetic catalog A', 'time_meaning': 'catalog creation time'}),
            2: Fact(2, 'shadowCopy', 9_000_000, 1, 2, 3,
                    {'artifact': 'synthetic catalog B', 'time_meaning': 'catalog creation time'}),
            3: Fact(3, 'programRun', 20_000_000, 1, 4, 5,
                    {'artifact': 'synthetic MuiCache key', 'source': 'MuiCache',
                     'time_meaning': 'registry key last-write; no per-program execution time'}),
        }

    def get(self, ids):
        return {fid: self.rows[fid] for fid in ids if fid in self.rows}

    def all(self):
        return list(self.rows.values())

    def string(self, sid):
        return self.strings[sid]


def load_reviewed_questions():
    base = Path(__file__).resolve().parent
    assembled = base / 'questions.json'
    if assembled.exists():
        return json.loads(assembled.read_text())['questions'], 'questions.json'
    rows = []
    for name in ('q01_20.json', 'q21_40.json', 'q41_60.json'):
        rows.extend(json.loads((base / 'parts' / name).read_text())['questions'])
    return rows, 'parts/q01_20.json + parts/q21_40.json + parts/q41_60.json'


def binding(candidate, question_id, path, field, **extra):
    return {'candidate_id': candidate['candidate_id'],
            'claim_sha256': claim_digest(candidate['claim']), 'question_id': question_id,
            'path': path, 'field': field, **extra}


def main():
    questions, contract_source = load_reviewed_questions()
    selected = [deepcopy(q) for q in questions if q['id'] in ('Q11', 'Q47')]
    assert len(selected) == 2, 'Both reviewed public questions must exist'
    public = {'schema_version': 2, 'case_id': 'synthetic-receipt-only',
              'time_zone': 'UTC', 'questions': selected}
    source = SyntheticSource()
    # Synthetic origin labels exercise the public source contract; this is not
    # a claim that these invented observations occur in the actual case.
    for row in source.rows.values():
        row.prov.update(image='pc.E01', exhibit='PC', source_snapshot='base-volume', source_variant='primary')
    scope_args = {'require_evidence_scope': True, 'evidence_facts_sha256': 'a' * 64}
    candidates = [{'candidate_id': 'SyntheticCopyA', 'claim': {'shadowCopyMade': [1]}},
                  {'candidate_id': 'SyntheticCopyB', 'claim': {'shadowCopyMade': [2]}},
                  {'candidate_id': 'SyntheticMuiCache', 'claim': {'programRan': [3]}}]
    receipts = []
    with tempfile.TemporaryDirectory(prefix='strict-public-synthetic-') as scratch:
        for candidate in candidates:
            cert = check(candidate['claim'], candidate['candidate_id'], source,
                         out_dir=Path(scratch))
            assert cert['status'] == 'verified', cert
            replay = verify(cert, source)
            assert replay == [], replay
            receipts.append({'candidate_id': candidate['candidate_id'], 'status': cert['status'],
                             'trust_tier': cert['trust_tier'], 'independent_replay_errors': replay})
    mixed = [binding(candidates[0], 'Q47', ['copies', 0, 'shadow_copy_id'], 'shadow_copy'),
             binding(candidates[1], 'Q47', ['copies', 0, 'created_at'], 'recorded_time_us', format='utc_iso')]
    nonexecution = binding(candidates[2], 'Q11', ['records', 0, 'path_or_application_id'], 'path')
    coherent = [binding(candidates[0], 'Q47', ['copies', 1, 'shadow_copy_id'], 'shadow_copy'),
                binding(candidates[0], 'Q47', ['copies', 1, 'created_at'], 'recorded_time_us', format='utc_iso')]
    # Legacy-only reconstruction: retain exact leaf roles, remove the reviewed
    # row policy, and explicitly select low-level non-strict legacy projection.
    # This is a receipt of the old weakness, never a recommended policy.
    old = deepcopy(public)
    q47 = next(q for q in old['questions'] if q['id'] == 'Q47')
    q47['answer_schema']['properties']['copies']['items'].pop('x-claim-row', None)
    old_plan = prepare_projection(old, candidates, mixed, source, require_claim_requirements=False, **scope_args)
    assert not old_plan['unsupported'] and len(old_plan['bindings']) == 2
    old_rendered = render_projection(old_plan)
    old_row = next(q for q in old_rendered['submission']['answers'] if q['question_id'] == 'Q47')['answer']['copies'][0]
    assert old_row == {'shadow_copy_id': 'SYNTHETIC-COPY-A', 'created_at': '1970-01-01T00:00:09Z'}
    assert source.rows[1].t != source.rows[2].t
    revised = prepare_projection(public, candidates, mixed + coherent + [nonexecution], source,
                                 require_claim_requirements=True, **scope_args)
    assert len(revised['bindings']) == 4, revised
    assert revised['frozen_conflicts'] == [{
        'reason': 'row_fields_require_same_claim_part', 'question_id': 'Q47',
        'path': ['copies', 0], 'binding_indices': [0, 1]}], revised['frozen_conflicts']
    rejected = {tuple(row['binding']['path']): row['reason'] for row in revised['unsupported']}
    assert rejected == {('records', 0, 'path_or_application_id'):
                        'claim_role_does_not_meet_public_requirement'}, rejected
    retained = render_projection(revised)
    expected = {'shadow_copy_id': 'SYNTHETIC-COPY-A', 'created_at': '1970-01-01T00:00:01Z'}
    retained_rows = next(q for q in retained['submission']['answers'] if q['question_id'] == 'Q47')['answer']['copies']
    assert retained_rows == [expected], retained_rows
    assert {tuple(row['output_path']) for row in retained['leaves']} == {
        ('copies', 0, 'created_at'), ('copies', 0, 'shadow_copy_id')}
    assert sorted(row['binding_index'] for row in retained['dropped']) == [0, 1]
    # Removing the conflicting B candidate must not reveal the A-only fragment
    # of the mixed row. Conflicts are frozen before whole-candidate filtering.
    filtered = render_projection(revised, admitted_ids=['SyntheticCopyA'])
    filtered_rows = next(q for q in filtered['submission']['answers'] if q['question_id'] == 'Q47')['answer']['copies']
    assert filtered_rows == [expected], filtered_rows
    assert sorted(row['binding_index'] for row in filtered['dropped']) == [0, 1]
    identifier_plan = prepare_projection(public, candidates, [mixed[0]], source,
                                         require_claim_requirements=True, **scope_args)
    assert not identifier_plan['unsupported'] and not identifier_plan['frozen_conflicts']
    identifier_only = render_projection(identifier_plan)
    identifier_row = next(q for q in identifier_only['submission']['answers'] if q['question_id'] == 'Q47')['answer']['copies'][0]
    assert identifier_row == {'shadow_copy_id': 'SYNTHETIC-COPY-A'}
    print(json.dumps({'scope': 'Synthetic facts only; no model, private keys, real case data or scoring.',
                      'contract_source': contract_source, 'certificates': receipts,
                      'legacy_only_per_leaf_counterexample': old_row,
                      'legacy_require_claim_requirements': False,
                      'legacy_row_policy_removed': True,
                      'revised_require_claim_requirements': True,
                      'require_evidence_scope': True,
                      'source_scope': 'Synthetic PC/base-volume/primary provenance with a caller-supplied synthetic digest, not actual case evidence.',
                      'actual_row_guard_conflicts': revised['frozen_conflicts'],
                      'revised_rejected': [{'path': list(path), 'reason': reason} for path, reason in rejected.items()],
                      'revised_retained_q47_rows': retained_rows,
                      'coherent_row_compacted_from_index': 1,
                      'coherent_row_compacted_to_index': 0,
                      'identifier_only_survives': identifier_row,
                      'candidate_filter_cannot_reveal_frozen_mixed_row': True,
                      'guard_meaning': 'Same claim-part row policy omits the mixed row, retains the coherent row and preserves frozen omissions during candidate filtering. This does not prove complete answers or question entailment.'}, indent=2))



if __name__ == '__main__':
    main()
