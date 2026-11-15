"""Offline public capability/work audit. No evidence inference, repair or scoring."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from agent.answer_projection import claim_digest
from agent.answer_requirements import inspect

LIMITATION = ('Public declarations and saved binding outcomes only. Catalog support does not establish '
              'source presence, relevance, completeness or truth. Missing bindings do not establish missing '
              'evidence or lack of investigation. No answer values are emitted and no answers are repaired. '
              'Input hashes identify supplied artifacts; they do not authenticate their origin.')
SCOPE_FAILURES = {'public_claim_scope_unavailable', 'evidence_facts_sha256_required',
                  'evidence_facts_sha256_mismatch', 'claim_scope_supporting_records_missing',
                  'claim_records_do_not_meet_public_scope', 'claim_supporting_records_have_mixed_origins'}


def _qid(row):
    if not isinstance(row, dict):
        return None
    binding = row.get('binding')
    value = row.get('question_id', binding.get('question_id') if isinstance(binding, dict) else None)
    return value if isinstance(value, str) else None


def audit_coverage(public, document, projection, catalog_snapshot, plan=None, *,
                   projection_catalog_sha256=None, allow_cross_revision=False):
    """Bind public/projection artifacts and inventory exact, explicitly observed gaps.

    A prepared projection plan supplies public lineage. Older plans did not bind a
    catalog; that lineage stays unverified unless its hash is separately supplied.
    Cross-revision mode compares declarations only; historical outcomes are not
    attributed to changed public rules.
    """
    if plan is None:
        plan = projection.get('projection')
    questions = public.get('questions') if isinstance(public, dict) else None
    if (not isinstance(questions, list) or not 1 <= len(questions) <= 100
            or any(not isinstance(q, dict) or not isinstance(q.get('id'), str) for q in questions)
            or len({q['id'] for q in questions}) != len(questions)):
        raise ValueError('invalid_public_questions')
    ids = {q['id'] for q in questions}
    if not isinstance(catalog_snapshot, dict) or not isinstance(catalog_snapshot.get('forms'), dict):
        raise ValueError('invalid_catalog_snapshot')
    if (not isinstance(plan, dict) or plan.get('projection_sha256') !=
            claim_digest({k: v for k, v in plan.items() if k != 'projection_sha256'})):
        raise ValueError('invalid_projection_plan_digest')
    if projection.get('projection_sha256') != plan['projection_sha256']:
        raise ValueError('projection_plan_mismatch')
    if (plan.get('case_id') != public.get('case_id') or
            projection.get('submission', {}).get('case_id') != public.get('case_id') or
            document.get('case_id') != public.get('case_id')):
        raise ValueError('case_mismatch')
    hashes = {name: claim_digest(value) for name, value in (
        ('public', public), ('document', document), ('projection', projection),
        ('catalog', catalog_snapshot), ('plan', plan))}
    mismatches = []
    if plan.get('public_sha256') != hashes['public']:
        mismatches.append('public_revision_mismatch')
    if projection_catalog_sha256 is not None and projection_catalog_sha256 != hashes['catalog']:
        mismatches.append('catalog_revision_mismatch')
    if mismatches and not allow_cross_revision:
        raise ValueError(','.join(mismatches))
    bindings = document.get('bindings')
    if not isinstance(bindings, list) or len(bindings) > 100000:
        raise ValueError('invalid_binding_document')
    # Malformed or foreign rows cannot silently vanish from question totals.
    groups = {'authored': bindings}
    for name in ('leaves', 'unsupported', 'dropped', 'conflicts'):
        value = projection.get(name, [])
        if not isinstance(value, list) or len(value) > 100000:
            raise ValueError('invalid_projection_rows')
        groups[name] = value
    unknown = {name: sum(_qid(row) not in ids for row in rows) for name, rows in groups.items()}
    counts = {name: Counter(_qid(row) for row in rows if _qid(row) in ids)
              for name, rows in groups.items()}
    statuses = {}
    for row in projection.get('submission', {}).get('answers', []):
        qid = _qid(row)
        if qid not in ids or qid in statuses or row.get('status') not in ('answered', 'unknown', 'unanswered'):
            raise ValueError('invalid_submission_status_rows')
        statuses[qid] = row['status']
    rows = []
    for question in questions:
        qid = question['id']
        inspected = inspect(question.get('answer_schema'), catalog_snapshot['forms'],
                            require_claim_requirements=True, require_evidence_scope=True)
        fields = []
        for requirement in inspected['requirements']:
            # Do not copy requirement prose, source values or offered bindings.
            fields.append({key: requirement[key] for key in ('path', 'branches', 'status', 'reason')
                           if key in requirement})
        declared = Counter(field['status'] for field in fields)
        unavailable = sum(s['status'] == 'unavailable' for s in inspected['scope_requirements'])
        categories = []
        if declared['no_catalog_support']:
            categories.append('catalog_or_mapping_gap')
        if declared['invalid'] or declared['missing_annotation']:
            categories.append('public_contract_review_needed')
        if unavailable:
            categories.append('declared_scope_unavailable')
        outcome = None
        if not mismatches:
            scope_indices = {i for i, r in enumerate(groups['unsupported'])
                             if _qid(r) == qid and r.get('reason') in SCOPE_FAILURES}
            meaning_indices = {i for i, r in enumerate(groups['unsupported']) if _qid(r) == qid and
                               any(c.get('status') != 'compatible' for c in r.get('meaning_checks', [])
                                   if isinstance(c, dict))}
            scope_rejected, meaning_rejected = len(scope_indices), len(meaning_indices)
            if not counts['authored'][qid]:
                categories.append('no_authored_binding')
            if scope_rejected:
                categories.append('recorded_scope_rejection')
            if meaning_rejected:
                categories.append('recorded_meaning_rejection')
            if counts['unsupported'][qid] > len(scope_indices | meaning_indices):
                categories.append('other_recorded_binding_rejection')
            if counts['dropped'][qid]:
                categories.append('recorded_binding_drop')
            if counts['conflicts'][qid]:
                categories.append('recorded_output_conflict')
            if counts['authored'][qid] and not counts['leaves'][qid]:
                categories.append('no_retained_leaf')
            outcome = {'answer_status': statuses.get(qid, 'not_supplied'),
                       **{name: counter[qid] for name, counter in counts.items()},
                       'scope_rejected': scope_rejected, 'meaning_rejected': meaning_rejected}
        rows.append({'question_id': qid, 'public_fields': fields,
                     'declaration_counts': dict(declared), 'unavailable_scopes': unavailable,
                     'categories': categories, 'binding_outcomes': outcome,
                     'source_presence': 'not_determined', 'investigation_status': 'not_determined',
                     'unsupported_meaning_vs_missing_implementation': 'requires_source_and_specification_review'})
    return {'schema_version': 1, 'status': 'development_diagnostic', 'case_id': public['case_id'],
            'input_sha256': hashes,
            'lineage': {'comparison': 'cross_revision_declarations_only' if mismatches else 'public_projection_aligned',
                        'mismatches': mismatches,
                        'catalog': 'caller_hash_matched' if projection_catalog_sha256 == hashes['catalog'] else
                                   'mismatched' if 'catalog_revision_mismatch' in mismatches else 'unverified',
                        'binding_document': 'supplied_artifact_not_authenticated_as_historical_checkpoint'},
            'unattributed_rows': unknown, 'questions': rows,
            'category_question_counts': dict(Counter(c for row in rows for c in row['categories'])),
            'accuracy': 'not_measured', 'limitation': LIMITATION}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('public', 'document', 'projection', 'catalog', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--plan', type=Path, help='Optional when projection contains its frozen plan.')
    parser.add_argument('--projection-catalog-sha256')
    parser.add_argument('--allow-cross-revision', action='store_true')
    args = parser.parse_args(argv)
    raw = {name: getattr(args, name).read_bytes()
           for name in ('public', 'document', 'projection', 'catalog')}
    if args.plan:
        raw['plan'] = args.plan.read_bytes()
    inputs = {name: json.loads(value) for name, value in raw.items()}
    result = audit_coverage(inputs['public'], inputs['document'], inputs['projection'], inputs['catalog'],
                            inputs.get('plan'), projection_catalog_sha256=args.projection_catalog_sha256,
                            allow_cross_revision=args.allow_cross_revision)
    result['input_file_sha256'] = {name: hashlib.sha256(value).hexdigest() for name, value in raw.items()}
    with args.out.open('x') as output:
        json.dump(result, output, indent=2)
        output.write('\n')
    print(json.dumps({'status': result['status'], 'questions': len(result['questions']),
                      'lineage': result['lineage'], 'accuracy': result['accuracy']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
