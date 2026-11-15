"""Bounded actual ShutdownTime precision check; no reference or model run."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace as NS
from unittest.mock import patch

from agent.answer_projection import claim_digest, project_answers
from agent.answer_store import project_bundle, public_profile, report_projection
from agent.timestamp_predicates import instant_ticks
from app import brief
from app.report import render_html
from checker.catalog import ROLES
from checker.check import check
from checker.facts import JsonFacts
from dissect.target import Target
from extractor import host_attributes, system
from extractor.store import Evidence, us
from verifier.verify import verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--readback', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    raw_receipt = args.readback.read_bytes()
    expected = json.loads(raw_receipt)
    target = Target.open(args.image)
    hive = next(h for h in system._hives(Evidence(), target) if h.name == 'SYSTEM' and not h.backup)
    with target.fs.path(hive.path).open('rb') as stream:
        hive_sha = hashlib.sha256(stream.read()).hexdigest()
    assert hive_sha == expected['source_hive_sha256']
    common = {'image': args.image.name, 'exhibit': 'HACK-PC', 'source_snapshot': 'base-volume', 'source_variant': 'primary'}
    ctx = {'common': common, 'examined_at': us(datetime.now(timezone.utc))}
    role = 'machine.last_shutdown'

    def extract():
        evidence = Evidence()
        with patch.object(system, '_hives', return_value=[hive]):
            host_attributes.extract(evidence, target, ctx)
        return evidence

    evidence = extract()
    facts = args.output / 'facts.json'
    evidence.write_json(facts, {'scope': 'selected real primary SYSTEM only'})
    source = JsonFacts(facts)
    digest = hashlib.sha256(facts.read_bytes()).hexdigest()
    value = next(r for r in source.all() if r.kind == ROLES[role].value_kind and r.prov.get('attribute_role') == role)
    native = json.loads(source.string(value.aux))
    assert native == expected['exact_shutdown_100ns']
    assert value.prov['registry_value_type'] == 3
    assert value.prov['native_filetime_le_hex'] == expected['raw_shutdown_filetime_hex']
    assert value.prov['native_filetime_ticks'] == expected['raw_shutdown_filetime_integer']
    assert instant_ticks(native) == expected['raw_shutdown_filetime_integer'] - 116444736000000000
    rows = {r.kind: r.id for r in source.all() if r.obj == value.obj}
    candidate = {'candidate_id': 'NativeShutdown', 'claim': {'attributeRecorded': [
        rows['attributeSubject'], rows[ROLES[role].kind], value.id, role]}}
    cert = check(candidate['claim'], candidate['candidate_id'], source, out_dir=args.output)
    assert cert['status'] == 'verified' and cert['axioms'] == []
    assert verify(cert, source) == []
    root = Path(__file__).resolve().parents[1]
    original = json.loads((root / 'eval/hacking_case_strict_draft/questions.json').read_text())
    question = deepcopy(next(q for q in original['questions'] if q['id'] == 'Q8'))
    # This is a separately labeled display diagnostic, not activation of the
    # review-only Hacking proposal or a change to the frozen benchmark.
    leaf = question['answer_schema']['properties']['shutdown_at']
    leaf.update(format='date-time', **{'x-claim-display': {'kind': 'report_timestamp_iso_v1', 'timezone': 'public_time_zone'}})
    public = {'schema_version': 2, 'case_id': 'independent-native-shutdown-display', 'time_zone': 'UTC',
              'instructions': ['Explicit UTC report display only; source fraction retained. No historical machine zone inferred.'],
              'questions': [question]}
    binding = {'candidate_id': candidate['candidate_id'], 'claim_sha256': claim_digest(candidate['claim']),
               'question_id': 'Q8', 'path': ['shutdown_at'], 'field': 'value'}

    def project(contract=public, offered=binding):
        return project_answers(contract, [candidate], [offered], source,
                               admitted_ids=[candidate['candidate_id']], require_claim_requirements=True,
                               require_evidence_scope=True, evidence_facts_sha256=digest)

    result = project()
    leaf_result, = result['leaves']
    assert not result['unsupported']
    assert leaf_result['source_value'] == native
    assert leaf_result['display']['fraction_digits'] == 7
    assert leaf_result['value'].endswith('.1092164+00:00')
    assert instant_ticks(leaf_result['value']) == instant_ticks(native)
    wrong = dict(binding, value=leaf_result['value'].replace('.1092164', '.109216'))
    assert not project(offered=wrong)['leaves']
    wrong_scope = deepcopy(public)
    wrong_scope['questions'][0]['answer_schema']['x-claim-scope']['origins'][0]['source_snapshot'] = 'vss:wrong'
    assert not project(contract=wrong_scope)['leaves']
    wrong_field = dict(binding, field='examined_at_us')
    assert not project(offered=wrong_field)['leaves']
    controls = ['literal_precision_repair_refused', 'wrong_snapshot_refused', 'examination_time_refused']
    original_open = system._open
    for kind in (0, 4, 5, 11):
        def open_key(ev, h, path):
            key = original_open(ev, h, path)
            if key is None or path.casefold() != (expected['control_set'] + r'\Control\Windows').casefold():
                return key
            values = [NS(name=v.name, value=v.value, type=kind if v.name.casefold() == 'shutdowntime' else v.type)
                      for v in key.values()]
            return NS(path=key.path, values=lambda: iter(values))
        with patch.object(system, '_open', side_effect=open_key):
            refused = extract()
        assert not any(json.loads(prov).get('attribute_role') == role for *_, prov in refused.rows())
        assert any('ShutdownTime' in issue for issue in refused.problems)
        controls.append('native_registry_type_' + str(kind) + '_refused')
    run = {'case': {'name': 'Native shutdown display diagnostic', 'facts_sha256': digest},
           'stats': {'verified': 1, 'rejected': 0}, 'findings': [cert], 'rejections': [], 'conclusions': [],
           'investigation': dict(public, facts_sha256=digest),
           'answer_bindings': {'schema_version': 1, 'case_id': public['case_id'], 'facts_sha256': digest, 'bindings': [binding]},
           'run_manifest': {'inputs': {'facts': {'sha256': digest}}}}
    run['answer_projection'] = project_bundle(run, public_profile(run['investigation']))
    assert report_projection(run)[1] is None
    report = render_html(run)
    assert html.escape(cert['english']) in report and '.1092164' in report
    assert brief.build(run)['counts']['dated'] == 0
    (args.output / 'report.html').write_text(report)
    (args.output / 'run.json').write_text(json.dumps(run, indent=2) + '\n')
    assert hashlib.sha256(facts.read_bytes()).hexdigest() == digest
    receipt = {'status': 'passed', 'runtime': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
               'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'source_readback_sha256': hashlib.sha256(raw_receipt).hexdigest(), 'source_hive_sha256': hive_sha,
               'facts_sha256': digest, 'exact_source_value': native, 'display_value': leaf_result['value'],
               'certificate_replayed': True, 'negative_controls': controls, 'reader_issues': evidence.problems,
               'whole_image_rehashed': False, 'scope': 'native source and explicit UTC display diagnostic only; no model, reference alignment or score'}
    (args.output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
