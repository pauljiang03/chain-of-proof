"""Common answer projection for A, its exact offline subset B, and checked C.

No model, reference, scorer, evidence repair or kernel invocation occurs here.
The runtime/replay must authenticate their own inputs and independently verify
certificates. This adapter checks exact claim binding and reports their recorded
acceptance; it never upgrades that receipt into an independent proof.
"""
from __future__ import annotations

from agent.answer_projection import claim_digest, project_answers, render_projection


def project_a(public, candidates, bindings, source):
    """Project every submitted A candidate, regardless of semantic validity."""
    return dict(project_answers(public, candidates, bindings, source, authority='unchecked'),
                arm='A', claim_authority='unchecked', source_repair=False)


def project_b(a_result, replay_rows):
    """Only remove whole candidates; never dereference evidence or change values."""
    if not isinstance(a_result, dict) or a_result.get('arm') != 'A':
        raise ValueError('B needs the frozen A projection')
    plan = a_result.get('projection')
    expected_a = render_projection(plan, authority='unchecked')
    # A's saved public projection must itself still be the unfiltered view.
    if any(a_result.get(key) != expected_a[key] for key in expected_a):
        raise ValueError('A output differs from its frozen unfiltered projection')
    if not isinstance(replay_rows, list) or len(replay_rows) != len(plan['candidates']):
        raise ValueError('replay must preserve every original A candidate in order')
    accepted, dispositions = [], []
    statuses = {'verified', 'rejected', 'malformed', 'unsupported', 'error'}
    for cid, row in zip(plan['candidates'], replay_rows):
        if (not isinstance(row, dict) or row.get('candidate_id') != cid
                or 'claim' not in row or claim_digest(row['claim']) != plan['candidates'][cid]['claim_sha256']):
            raise ValueError('replay candidate identity, order or exact claim differs from A')
        status = row.get('status')
        if status not in statuses:
            raise ValueError('unknown replay disposition')
        if status == 'verified':
            receipt = row.get('verification')
            if row.get('checker_status') != 'verified' or not isinstance(receipt, dict) or receipt.get('passed') is not True:
                raise ValueError('accepted replay lacks its independent-verification receipt')
            accepted.append(cid)
        dispositions.append({'candidate_id': cid, 'status': status})
    result = render_projection(plan, admitted_ids=accepted, authority='recorded_certificates')
    return dict(result, projection=plan, arm='B', source_arm='A', source_repair=False,
                disposition=dispositions, model_calls=0,
                replay_scope='Acceptance and replay results are recorded receipts. This projector does not reverify or authenticate them.')


def project_c(public, proposals, bindings, source):
    """Use the identical field engine, retaining recorded verified C proposals only."""
    if not isinstance(proposals, list) or any(not isinstance(row, dict) for row in proposals):
        raise ValueError('C proposals must be a list of recorded proposal objects')
    accepted = [row.get('candidate_id', row.get('finding_id')) for row in proposals if row.get('status') == 'verified']
    return dict(project_answers(public, proposals, bindings, source, admitted_ids=accepted,
                                authority='recorded_certificates'), arm='C', source_repair=False,
                replay_scope='Recorded verified status is supplied by the checked runtime; independent certificate replay remains separate.')
