"""Assemble a public-only review derivative; never read a reference or score a run."""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from agent.answer_projection import catalog
from agent.answer_requirements import KEY, ROW_KEY, inspect
from agent.case import read_question_profile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
ORIGINAL = ROOT / 'eval/benchmark_nist_questions.json'
PARTS = ('q01_20.json', 'q21_40.json', 'q41_60.json')
CASE_ID = 'nist-cfreds-data-leakage-strict-review-v1'


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()


def fingerprint(path):
    raw = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def without_annotations(value):
    if isinstance(value, dict):
        return {key: without_annotations(child) for key, child in value.items() if key not in (KEY, ROW_KEY)}
    if isinstance(value, list):
        return [without_annotations(child) for child in value]
    return value


def build():
    original = read_question_profile(ORIGINAL)
    questions, reviews = [], []
    for name in PARTS:
        part = json.loads((HERE / 'parts' / name).read_text())
        if set(part) != {'questions', 'reviews'} or len(part['questions']) != 20:
            raise ValueError('unexpected public review part: ' + name)
        questions.extend(part['questions'])
        reviews.extend(part['reviews'])
    if without_annotations(questions) != original['questions']:
        raise ValueError('draft changed a public prompt, field, shape or matching rule')
    if [row['question_id'] for row in reviews] != [q['id'] for q in questions]:
        raise ValueError('reviews do not cover the public questions exactly')

    public = deepcopy(original)
    public.update(case_id=CASE_ID, contract_revision='strict-public-review-v1-draft',
                  title='Data Leakage: strict public meaning review (not approved for a model run)',
                  questions=questions)
    public['instructions'] += [
        'This is a separate public-only review derivative. It is not a scored benchmark revision or authorization to run an experiment.',
        'Each declared requirement describes the full requested field meaning. A needs_* role names missing support; it is not a new proof rule.',
        'Supported individual fields remain partial observations. Complete lists, attribution and relationships between separately bound fields are not established.',
        'Reviewed row policies require the same atomic claim part where fields describe one record or relation. Independent policies apply only to explicitly separate sections.',
        'Selected-exhibit requirements and missing stronger meanings remain launch blockers in review.json. Do not launch this draft until those checks are implemented and independently reviewed.',
        'Keep narrower observations in a separate evidence report. Do not place them in stronger answer fields or change their labels to obtain support.',
    ]
    forms = catalog()['forms']
    field_rows, row_policies, counts, per_question = [], [], Counter(), []
    for question in questions:
        preflight = inspect(question['answer_schema'], forms, require_claim_requirements=True)
        rows = preflight['requirements']
        row_policies.extend({'question_id': question['id'], **row} for row in preflight['row_requirements'])
        statuses = Counter(row['status'] for row in rows)
        if statuses['missing_annotation'] or statuses['invalid']:
            raise ValueError('incomplete or invalid declarations in ' + question['id'])
        counts.update(statuses)
        per_question.append({'question_id': question['id'], 'leaf_occurrences': len(rows),
                             'catalog_supported': statuses['catalog_support'],
                             'explicitly_unsupported': statuses['no_catalog_support']})
        for row in rows:
            field_rows.append({'question_id': question['id'], 'path': row['path'],
                               'branches': row.get('branches', []), 'status': row['status'],
                               'available_fields': row.get('available_fields', []),
                               'evidence_needed': row['requirement']['evidence_needed']})
    peers = [json.loads((HERE / 'parts' / ('peer_' + name)).read_text()) for name in PARTS]
    inputs = [ORIGINAL, ROOT / 'eval/QUESTIONS.md', ROOT / 'agent/answer_projection.py',
              ROOT / 'agent/answer_requirements.py', ROOT / 'checker/catalog.py',
              *(HERE / 'parts' / name for name in PARTS),
              *(HERE / 'parts' / ('peer_' + name) for name in PARTS)]
    report = {
        'schema_version': 1, 'case_id': CASE_ID,
        'status': 'reviewed_draft_with_launch_blockers', 'model_run_ready': False,
        'scope': 'Public prompts, schema, catalog and source meanings only. No case answers, private reference, score or model experiment.',
        'original_questions_preserved_except_added_requirements': True,
        'original_inputs': [fingerprint(path) for path in inputs],
        'counts': {'questions': len(questions), 'leaf_occurrences_including_anyof_branches': len(field_rows),
                   'catalog_supported': counts['catalog_support'],
                   'explicitly_unsupported': counts['no_catalog_support'],
                   'missing_or_invalid': 0,
                   'row_policies': len(row_policies),
                   'same_claim_part_policies': sum(row['mode'] == 'same_claim_part' for row in row_policies),
                   'independent_section_policies': sum(row['mode'] == 'independent' for row in row_policies),
                   'questions_with_any_catalog_supported_leaf': sum(q['catalog_supported'] > 0 for q in per_question)},
        'count_meaning': 'Catalog compatibility counts, not available case evidence, certified answers, accuracy or complete questions.',
        'launch_blockers': [
            {'id': 'selected_exhibit_scope', 'requirement': 'Bind answer fields to the intended PC, USB or CD exhibit and snapshot. Existing exact roles do not by themselves enforce the public question scope.'},
            {'id': 'cross_claim_subject_joins', 'requirement': 'The declared same-atomic-part guard is implemented. Fields needing joins across separate claims remain unsupported until approved compound forms establish the required shared subject and roles.'},
            {'id': 'missing_meaning_rules', 'requirement': 'Add evidence and reviewed rules for requested actions, chronology, source-specific timestamps, attribution and recovery. A generic path, timestamp or record kind cannot stand in for those meanings.'},
            {'id': 'separate_scoring_revision', 'requirement': 'Any scoring use needs an explicitly frozen compatible derivative and comparison plan. No reference or scores were created or changed here.'},
        ],
        'peer_resolution_policy': 'Retain exact partial observations and coherent same-atomic-part rows; withhold unsupported cross-claim joins and nonexecution paths. Peer reports describe the earlier draft and author reviews record the resolutions.',
        'per_question': per_question, 'fields': field_rows, 'row_policies': row_policies,
        'author_reviews': reviews, 'peer_reviews': peers,
    }
    return {'questions.json': public, 'review.json': report}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='check committed derived outputs without changing files')
    args = parser.parse_args()
    outputs = build()
    for name, value in outputs.items():
        path = HERE / name
        raw = encoded(value)
        if args.check:
            if not path.exists() or path.read_bytes() != raw:
                raise ValueError('derived review output is stale: ' + name)
        else:
            path.write_bytes(raw)
    read_question_profile(HERE / 'questions.json')
    print(json.dumps({'status': outputs['review.json']['status'],
                      'model_run_ready': False, **outputs['review.json']['counts']}, sort_keys=True))


if __name__ == '__main__':
    main()
