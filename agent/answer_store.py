"""Save explicit question bindings and rebuild values from recorded certificates.

The projection code is part of the trusted renderer, like the English renderer.
Question placement and completeness are not Lean theorems. Independent certificate
replay remains a separate operation; this module does not confer proof authority.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from agent.investigation import Investigation, _read_json, atomic_json, current_certificates
from checker import claims
from checker.facts import Fact, FactSource

FILENAME = 'answer-bindings.json'
MAX_BINDINGS = 20000
MAX_BATCH = 1000


class CertificateSource(FactSource):
    """Only the source fields already bound into the selected certificates."""

    def __init__(self, certificates):
        self.facts, self.strings = {}, {}
        for certificate in certificates:
            for row in certificate.get('cited_facts', []):
                fact = Fact(row['id'], row['kind'], row['t'], row['res'], row['obj'], row['aux'], row.get('prov', {}))
                if fact.row_sha256() != row.get('row_sha256'):
                    raise ValueError('certificate row hash does not match its recorded fields')
                previous = self.facts.get(fact.id)
                if previous is not None and previous.row_sha256() != fact.row_sha256():
                    raise ValueError('certificates disagree about the same source row')
                self.facts[fact.id] = fact
                for field in ('obj', 'aux'):
                    sid, value = row[field], row[field + '_text']
                    if not isinstance(value, str) or (sid in self.strings and self.strings[sid] != value):
                        raise ValueError('certificates disagree about an interned source value')
                    self.strings[sid] = value

    def get(self, ids):
        return {i: self.facts[i] for i in ids if i in self.facts}

    def string(self, sid):
        if sid not in self.strings:
            raise ValueError('projected string is absent from the cited certificates')
        return self.strings[sid]

    def all(self):
        return [self.facts[i] for i in sorted(self.facts)]

    def check_sentences(self, certificates):
        """Check copied strings against the certificate's fixed English rendering.

        This detects internal disagreement, not a coherent replacement of the
        whole bundle. Only replay against the original source establishes that.
        """
        for certificate in certificates:
            claim = claims.parse(certificate['claim'])
            ids, found = claims.cited_facts(claim, self)
            if ids != [row['id'] for row in certificate['cited_facts']]:
                raise ValueError('certificate cited-row scope differs from its claim')
            if claims.english(claim, found, self) != certificate.get('english'):
                raise ValueError('certificate strings disagree with its recorded sentence')


def public_profile(state):
    """Keep public question shapes only; never use a scoring reference."""
    if not isinstance(state.get('case_id'), str) or not state['case_id']:
        raise ValueError('typed answers require a public case_id')
    return {'schema_version': 2, 'case_id': state['case_id'],
            'time_zone': state.get('time_zone'),
            'questions': [{'id': row['id'], 'prompt': row['prompt'],
                           'answer_schema': deepcopy(row.get('answer_schema', {}))}
                          for row in state['questions']]}


def _document(path, state):
    if path.exists() or path.is_symlink():
        doc = _read_json(path)
        if (not isinstance(doc, dict) or doc.get('schema_version') != 1
                or doc.get('case_id') != state['case_id']
                or doc.get('run_id') != state['run_id']
                or doc.get('facts_sha256') != state.get('facts_sha256')
                or not isinstance(doc.get('bindings'), list)
                or len(doc['bindings']) > MAX_BINDINGS):
            raise ValueError('answer bindings do not belong to this investigation')
        return doc
    return {'schema_version': 1, 'case_id': state['case_id'], 'run_id': state['run_id'],
            'facts_sha256': state.get('facts_sha256'), 'bindings': []}


def _project(state, document, certificates):
    from agent.answer_projection import project_answers
    source = CertificateSource(certificates.values())
    source.check_sentences(certificates.values())
    return project_answers(public_profile(state), list(certificates.values()), document['bindings'],
                           source,
                           admitted_ids=set(certificates), authority='recorded_certificates')


def _certificates(directory, bindings):
    ids = list(dict.fromkeys(b.get('candidate_id') for b in bindings if isinstance(b, dict)))
    result = {}
    # The certificate reader also serves short work-note updates. Batching avoids
    # imposing that UI's per-call limit on a complete answer inventory.
    for start in range(0, len(ids), 256):
        result.update(current_certificates(directory, ids[start:start + 256]))
    return result


def answer(run_dir, question_id, bindings=None, *, replace=False):
    """Read a field catalog or add explicit bindings to current-run certificates.

    An empty replacement clears that question's bindings. The tool audit keeps
    prior calls. No candidate or proof is edited by an answer update.
    """
    from agent.answer_projection import catalog, claim_digest
    planner = Investigation(run_dir)
    with planner._locked():
        state = planner._load()
        if question_id not in {q['id'] for q in state['questions']}:
            raise ValueError('question_id must name a current public question')
        if type(replace) is not bool:
            raise ValueError('replace must be a Boolean')
        path = Path(run_dir) / FILENAME
        document = _document(path, state)
        if bindings is None:
            if replace:
                raise ValueError('replace requires a bindings list')
            return {'question_id': question_id, 'field_catalog': catalog(),
                    'bindings': [b for b in document['bindings'] if b.get('question_id') == question_id]}
        if not isinstance(bindings, list) or len(bindings) > MAX_BATCH:
            raise ValueError(f'bindings must be a list of at most {MAX_BATCH} entries')
        prepared = []
        for raw in bindings:
            if not isinstance(raw, dict) or set(raw) - {'finding_id', 'candidate_id', 'claim_sha256', 'part', 'field', 'path', 'format', 'value'}:
                raise ValueError('unsupported answer binding fields')
            row = deepcopy(raw)
            fid = row.pop('finding_id', row.get('candidate_id'))
            if 'candidate_id' in row and row['candidate_id'] != fid:
                raise ValueError('conflicting finding_id and candidate_id')
            row.update(candidate_id=fid, question_id=question_id)
            row.setdefault('part', 0)
            prepared.append(row)
        certificates = _certificates(run_dir, prepared)
        for row in prepared:
            digest = claim_digest(certificates[row['candidate_id']]['claim'])
            if row.get('claim_sha256', digest) != digest:
                raise ValueError('binding hash differs from the recorded claim')
            row['claim_sha256'] = digest
        combined = [b for b in document['bindings'] if not replace or b.get('question_id') != question_id]
        seen = {json.dumps(b, sort_keys=True, allow_nan=False) for b in combined}
        for row in prepared:
            key = json.dumps(row, sort_keys=True, allow_nan=False)
            if key not in seen:
                combined.append(row)
                seen.add(key)
        if len(combined) > MAX_BINDINGS:
            raise ValueError('answer binding limit reached; continue in a new run')
        document['bindings'] = combined
        certificates = _certificates(run_dir, combined)
        projection = _project(state, document, certificates)
        atomic_json(path, document)
        atomic_json(Path(run_dir) / 'projected-answers.json', projection)
        return projection


def enrich_bundle(run, run_dir):
    """Rebuild a saved answer view; never trust the previous projected values."""
    directory = Path(run_dir)
    path = directory / FILENAME
    if not path.exists() and not path.is_symlink():
        return run
    state = Investigation(directory).snapshot()
    document = _document(path, state)
    certificates = _certificates(directory, document['bindings'])
    selected = {f['finding_id']: f for f in run.get('findings', []) if isinstance(f, dict) and 'finding_id' in f}
    for fid, cert in certificates.items():
        bundled = selected.get(fid)
        if bundled is None or any(bundled.get(key) != cert.get(key) for key in ('claim', 'cited_facts', 'status')):
            raise ValueError('answer certificate differs from the exported run')
    run['answer_projection'] = _project(state, document, certificates)
    run['answer_bindings'] = deepcopy(document)
    atomic_json(directory / 'projected-answers.json', run['answer_projection'])
    return run


def read_projection(run_dir):
    """Recompute a bound answer snapshot for neutral coverage diagnostics."""
    directory = Path(run_dir)
    path = directory / FILENAME
    if not path.exists() and not path.is_symlink():
        return None
    planner = Investigation(directory)
    with planner._locked():
        state = planner._load()
        document = _document(path, state)
        return _project(state, document, _certificates(directory, document['bindings']))


def project_bundle(run, public, *, authority='recorded_certificates'):
    """Recompute typed answers from bundled claims after independent verification.

    Callers must verify the certificates before labelling the result independently
    replayed. This function alone checks bindings, not Lean proofs.
    """
    from agent.answer_projection import project_answers
    document = run.get('answer_bindings')
    state = run.get('investigation', {})
    projection_public = public
    if document is None:
        document = {'schema_version': 1, 'case_id': public['case_id'], 'bindings': []}
    if (not isinstance(document, dict) or document.get('schema_version') != 1
            or document.get('case_id') != public['case_id']
            or not isinstance(document.get('bindings'), list)
            or len(document['bindings']) > MAX_BINDINGS):
        raise ValueError('invalid bundled answer bindings')
    if document.get('run_id') is not None:
        if (document.get('run_id') != state.get('run_id')
                or document.get('facts_sha256') != state.get('facts_sha256')
                or state.get('case_id') != public['case_id']):
            raise ValueError('bundled answer bindings belong to another investigation')
        stored = public_profile(state)
        expected = [{key: q[key] for key in ('id', 'prompt', 'answer_schema') if key in q}
                    for q in public['questions']]
        if stored['questions'] != expected or stored.get('time_zone') != public.get('time_zone'):
            raise ValueError('public questions differ from the bound investigation')
        projection_public = stored
    certificates = {}
    requested = {b.get('candidate_id') for b in document['bindings'] if isinstance(b, dict)}
    for cert in run.get('findings', []):
        if not isinstance(cert, dict) or cert.get('status') != 'verified':
            continue
        fid = cert.get('finding_id')
        if fid not in requested:
            continue
        if fid in certificates:
            raise ValueError('duplicate bundled finding ID')
        certificates[fid] = cert
    if requested != set(certificates):
        raise ValueError('answer binding has no unique verified certificate in this bundle')
    source = CertificateSource(certificates.values())
    source.check_sentences(certificates.values())
    return project_answers(projection_public, list(certificates.values()), document['bindings'],
                           source,
                           admitted_ids=set(certificates), authority=authority)


def report_projection(run):
    """Validate the saved view against its bound fields before showing it as such."""
    try:
        result = project_bundle(run, public_profile(run.get('investigation', {})))
        if result != run.get('answer_projection'):
            raise ValueError('saved answer projection differs from its claim bindings')
        return result, None
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        return None, str(error)
