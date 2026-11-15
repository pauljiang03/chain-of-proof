"""Selected actual-source integration probe, never a benchmark or model run.

Run with --facts pointing to a NEW selected-reader snapshot and --output to a
new audit directory. No input is modified. Source locators must be independently
read back before interpreting this as a byte-to-answer validation.
"""
from collections import defaultdict
from copy import deepcopy
import argparse
import hashlib
import html
import json
from pathlib import Path
import struct
import subprocess

from agent.answer_projection import claim_digest, project_answers
from agent.answer_store import project_bundle, public_profile, report_projection
from app import brief, narrative
from app.report import render_html, report_options
from checker.catalog import ROLES
from checker.check import check
from checker.facts import JsonFacts
from checker.report import render as render_markdown
from eval.data_leakage_strict_draft.assemble import build
from verifier.verify import verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--facts', required=True, type=Path)
    parser.add_argument('--source-validation', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    digest = hashlib.sha256(args.facts.read_bytes()).hexdigest()
    source = JsonFacts(args.facts)
    source_validation_bytes = args.source_validation.read_bytes()
    source_validation_digest = hashlib.sha256(source_validation_bytes).hexdigest()
    raw_check = json.loads(source_validation_bytes)
    assert raw_check['status'] == 'passed'
    public = build()['questions.json']
    public['questions'] = [q for q in public['questions'] if q['id'] in ('Q2', 'Q46', 'Q50')]
    groups = defaultdict(dict)
    subjects = {row.obj: source.string(row.aux) for row in source.all() if row.kind == 'attributeSubject'}
    for row in source.all():
        role = row.prov.get('attribute_role')
        if role in ROLES and row.kind == ROLES[role].value_kind:
            rows = {r.kind: r.id for r in source.all() if r.obj == row.obj}
            groups[subjects[row.obj]][role] = {
                'value': json.loads(source.string(row.aux)), 'provenance': row.prov,
                'entry': [rows['attributeSubject'], rows[ROLES[role].kind], row.id, role]}
    q2_roles = ['partition.' + name for name in ('number', 'bootable', 'filesystem', 'start_sector', 'total_sectors')]
    q46_roles = ['search.index.' + name for name in ('item_path', 'date_created', 'container_path', 'table', 'document_id')]
    q50_roles = ['snapshot.exclusion.' + name for name in ('registry_key', 'value_name', 'pattern')]
    partition = next(g for g in groups.values() if set(q2_roles) <= g.keys())
    other_partition = next(g for g in groups.values() if set(q2_roles) <= g.keys() and g is not partition)
    for group in (partition, other_partition):
        prov = group['partition.number']['provenance']
        raw = bytes.fromhex(raw_check['MBR'][str(prov['disk_index'])]['sector_hex'])
        assert hashlib.sha256(raw).hexdigest() == prov['mbr_sha256']
        offset = 446 + 16 * (group['partition.number']['value'] - 1)
        start, sectors = struct.unpack_from('<II', raw, offset + 8)
        assert (raw[offset] == 0x80) == group['partition.bootable']['value']
        assert start == group['partition.start_sector']['value']
        assert sectors == group['partition.total_sectors']['value']
        assert raw[offset:offset + 16].hex() == prov['mbr_entry_hex']
    desktop = next(g for g in groups.values() if set(q46_roles) <= g.keys()
                   and g['search.index.document_id']['value'] == raw_check['ESE']['document_id']
                   and g['search.index.table']['value'] == raw_check['ESE']['table'])
    assert desktop['search.index.item_path']['value'] == raw_check['ESE']['indexed_path']
    assert desktop['search.index.date_created']['value'] == raw_check['ESE']['independent_date_created']
    exclusion = next(g for g in groups.values() if set(q50_roles) <= g.keys()
                     and g['snapshot.exclusion.value_name']['value'] == raw_check['registry']['value_name'])
    assert exclusion['snapshot.exclusion.pattern']['value'] in raw_check['registry']['literal_multi_string']
    other_exclusion = next(g for g in groups.values() if set(q50_roles) <= g.keys()
                           and g['snapshot.exclusion.value_name']['value'] != 'OutlookOST')
    results, certs, all_bindings = [], [], []

    def make(name, group, roles):
        return {'candidate_id': name, 'claim': {'attributeTuple': [group[role]['entry'] for role in roles]}}

    def certify(candidate, accepted=True):
        cert = check(candidate['claim'], candidate['candidate_id'], source, out_dir=args.output)
        assert (cert['status'] == 'verified') == accepted, cert
        if accepted:
            assert cert['axioms'] == [] and cert['trust_tier'] == 'kernel', cert
            assert verify(cert, source) == []
        return cert

    def bindings(candidate, qid, fields):
        return [{'candidate_id': candidate['candidate_id'], 'claim_sha256': claim_digest(candidate['claim']),
                 'question_id': qid, 'path': path, 'field': field, 'part': 0} for path, field in fields]

    def project(candidate, bound, *, contract=public, admitted=True):
        return project_answers(contract, [candidate], bound, source,
                               admitted_ids=[candidate['candidate_id']] if admitted else [],
                               require_claim_requirements=True, require_evidence_scope=True,
                               evidence_facts_sha256=digest)

    specs = [('Q2', partition, q2_roles, [(['partitions', 0, field], 'value_' + str(i))
              for i, field in enumerate(('number', 'bootable', 'filesystem', 'start_sector', 'total_sectors'))]),
             ('Q46', desktop, q46_roles, [(['records', 0, 'path'], 'value_0'), (['records', 0, 'date_created'], 'value_1')]),
             ('Q50', exclusion, q50_roles, [([field], 'value_' + str(i))
              for i, field in enumerate(('registry_key', 'value_name', 'pattern'))])]
    for qid, group, roles, fields in specs:
        candidate = make('Actual' + qid, group, roles)
        cert = certify(candidate)
        bound = bindings(candidate, qid, fields)
        result = project(candidate, bound)
        assert not result['unsupported'] and len(result['leaves']) == len(fields), result['unsupported']
        for path, field in fields:
            expected = group[roles[int(field.split('_')[1])]]['value']
            actual = next(leaf['value'] for leaf in result['leaves'] if leaf['path'] == path)
            assert type(actual) is type(expected) and actual == expected, (qid, path, actual, expected)
        results.append({'control': qid + '_positive', 'status': 'passed', 'leaves': len(result['leaves']),
                        'values': [leaf['value'] for leaf in result['leaves']]})
        (args.output / (qid + '-projection.json')).write_text(json.dumps(result, indent=2) + '\n')
        certs.append(cert)
        all_bindings.extend(bound)

    def refused(label, candidate, bound, *, contract=public, kernel_accept=True):
        certify(candidate, accepted=kernel_accept)
        result = project(candidate, bound, contract=contract, admitted=kernel_accept)
        assert not result['leaves'], (label, result['leaves'])
        results.append({'control': label, 'status': 'passed', 'kernel_accepted': kernel_accept,
                        'reasons': sorted({r['reason'] for r in result['unsupported']})})
        (args.output / (label + '.json')).write_text(json.dumps(result, indent=2) + '\n')

    mixed = make('MixedPartition', partition, q2_roles)
    mixed['claim']['attributeTuple'][0] = other_partition[q2_roles[0]]['entry']
    refused('Q2_mixed_identity', mixed, bindings(mixed, 'Q2', [(['partitions', 0, 'number'], 'value_0')]), kernel_accept=False)
    wrong_scope = deepcopy(public)
    next(q for q in wrong_scope['questions'] if q['id'] == 'Q2')['answer_schema']['x-claim-scope']['origins'][0].update(
        source_snapshot='base-volume', source_variant='primary')
    candidate = make('WrongPartitionScope', partition, q2_roles)
    refused('Q2_wrong_scope', candidate, bindings(candidate, 'Q2', [(['partitions', 0, 'number'], 'value_0')]), contract=wrong_scope)
    candidate = make('NoPrintedSize', partition, q2_roles)
    refused('Q2_no_printed_size', candidate, bindings(candidate, 'Q2', [(['partitions', 0, 'size_as_printed'], 'value_4')]))
    candidate = make('ModifiedNotCreated', desktop, q46_roles)
    candidate['claim']['attributeTuple'][1] = desktop['search.index.date_modified']['entry']
    refused('Q46_wrong_time_role', candidate, bindings(candidate, 'Q46', [(['records', 0, 'date_created'], 'value_1')]))
    candidate = make('ExamNotCreated', desktop, q46_roles)
    refused('Q46_exam_time', candidate, bindings(candidate, 'Q46', [(['records', 0, 'date_created'], 'examined_at_us')]))
    candidate = make('NonDesktop', next(g for g in groups.values() if set(q46_roles) <= g.keys()
                     and '\\desktop\\' not in g['search.index.item_path']['value'].lower()), q46_roles)
    refused('Q46_other_directory', candidate, bindings(candidate, 'Q46', [(['records', 0, 'path'], 'value_0')]))
    candidate = make('WrongExclusion', other_exclusion, q50_roles)
    refused('Q50_other_registry_value', candidate, bindings(candidate, 'Q50', [(['pattern'], 'value_2')]))
    candidate = make('NoOmissionCause', exclusion, q50_roles)
    refused('Q50_no_effective_omission', candidate, bindings(candidate, 'Q50', [(['ost_files_excluded'], 'value_2')]))
    run = {'case': {'name': 'Selected actual-source integration probe', 'facts_sha256': digest},
           'stats': {'verified': len(certs), 'rejected': 0, 'proposals': len(certs)}, 'findings': certs,
           'rejections': [], 'conclusions': [], 'investigation': dict(public, facts_sha256=digest),
           'answer_bindings': {'schema_version': 1, 'case_id': public['case_id'], 'facts_sha256': digest, 'bindings': all_bindings},
           'run_manifest': {'inputs': {'facts': {'sha256': digest}}}}
    run['answer_projection'] = project_bundle(run, public_profile(run['investigation']))
    assert report_projection(run)[1] is None
    full, short, md = render_html(run), render_html(run, report_options(brief=True, sections=[])), render_markdown(run)
    for cert in certs:
        assert html.escape(cert['english']) in full
    for output in (html.unescape(full), md):
        assert 'Structured answers from claim fields' in output
        assert 'ost_files_excluded' not in output.split('Structured answers from claim fields')[1].split('Field links and omitted')[0]
    info = brief.build(run)
    assert info['counts']['dated'] == 0 and info['days'] == []
    assert narrative.build(run)['points'] == []
    (args.output / 'run.json').write_text(json.dumps(run, indent=2) + '\n')
    for name, value in [('report.html', full), ('short.html', short), ('report.md', md)]:
        (args.output / name).write_text(value)
    assert hashlib.sha256(args.facts.read_bytes()).hexdigest() == digest
    receipt = {'status': 'passed', 'runtime': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
               'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'facts_sha256': digest, 'source_validation_sha256': source_validation_digest,
               'controls': results, 'positive_certificates': 3, 'positive_projected_fields': len(run['answer_projection']['leaves']),
               'db_state': raw_check['ESE']['db_state'], 'logs_replayed': False, 'scope': 'selected source controls, no model run or accuracy score',
               'whole_image_rehashed': False}
    (args.output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
