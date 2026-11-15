"""Save answer bindings and rebuild their values from recorded certificates."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from agent.investigation import Investigation, _read_json, atomic_json, current_certificates
from checker import claims
from checker.facts import Fact, FactSource, open_source

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
        """Check copied sentences against the certificate's own English rendering.

        This catches internal disagreement only; replay against the source catches a
        wholly replaced bundle.
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


def _scoped(state, bindings):
    """True when an applicable declaration limits answers to the selected source records."""
    from agent.answer_requirements import applicable_scopes
    questions = {row['id']: row for row in state.get('questions', [])}
    for binding in bindings:
        question = questions.get(binding.get('question_id'))
        if question is None:
            continue
        try:
            scopes = applicable_scopes(question.get('answer_schema', {}), binding.get('path'),
                                       require_evidence_scope=True)
        except (ValueError, TypeError, KeyError):
            continue  # the projector reports this error
        if any(scope['mode'] == 'source_records' for scope in scopes):
            return True
    return False


def _evidence_context(directory, state, document, certificates, source=None, digest=None):
    """Bind scoped projections to the actual source rows, not to what certificates say."""
    from agent.run_manifest import file_binding
    import re
    if (source is None) != (digest is None):
        raise ValueError('internal answer evidence source and digest must be supplied together')
    if digest is not None and (not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest)):
        raise ValueError('internal answer evidence digest must be a valid SHA-256')
    manifest_path = Path(directory) / 'run-manifest.json'
    manifest = _read_json(manifest_path) if manifest_path.exists() or manifest_path.is_symlink() else None
    recorded = manifest.get('inputs', {}).get('facts', {}) if isinstance(manifest, dict) else {}
    declared = [state.get('facts_sha256'), document.get('facts_sha256'), recorded.get('sha256')]
    if any(value is not None for value in declared) and len(set(declared)) != 1:
        raise ValueError('answer evidence digest differs across manifest, investigation and bindings')
    if not _scoped(state, document['bindings']):
        if digest is not None and declared[0] is not None and digest != declared[0]:
            raise ValueError('actual evidence differs from the bound investigation')
        return declared[0]
    if not all(isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) for value in declared):
        raise ValueError('source-scoped answers require a bound evidence SHA-256')
    owned_source = None
    try:
        if source is None:
            path = recorded.get('path')
            if not isinstance(path, str) or not path:
                raise ValueError('source-scoped answers require the bound facts path')
            before = Path(path).stat()
            binding = file_binding(path)
            digest = binding['sha256']
            if digest != declared[0]:
                raise ValueError('actual evidence differs from the bound investigation')
            source = open_source(path)
            owned_source = source
            after = Path(path).stat()
            fingerprint = lambda stat: (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
            if fingerprint(before) != fingerprint(after):
                raise ValueError('evidence changed while loading answer source')
        if digest != declared[0]:
            raise ValueError('actual evidence differs from the bound investigation')
        for certificate in certificates.values():
            rows = certificate.get('cited_facts', [])
            found = source.get([row['id'] for row in rows])
            for row in rows:
                fact = found.get(row['id'])
                if (fact is None or fact.row_sha256() != row.get('row_sha256')
                        or any(getattr(fact, key) != row.get(key) for key in ('kind', 't', 'res', 'obj', 'aux', 'prov'))
                        or any(source.string(getattr(fact, key)) != row.get(key + '_text') for key in ('obj', 'aux'))):
                    raise ValueError('answer certificate row differs from the bound evidence source')
        return digest
    finally:
        if owned_source is not None:
            close = getattr(owned_source, 'close', None)
            if close is None:
                close = getattr(getattr(owned_source, '_db', None), 'close', None)
            if close is not None:
                close()


def _project(state, document, certificates, *, evidence_facts_sha256=None):
    from agent.answer_projection import project_answers
    source = CertificateSource(certificates.values())
    source.check_sentences(certificates.values())
    return project_answers(public_profile(state), list(certificates.values()), document['bindings'],
                           source,
                           admitted_ids=set(certificates), authority='recorded_certificates', require_claim_requirements=True,
                           require_evidence_scope=True, evidence_facts_sha256=evidence_facts_sha256)


def _certificates(directory, bindings):
    ids = list(dict.fromkeys(b.get('candidate_id') for b in bindings if isinstance(b, dict)))
    result = {}
    # Read in batches to stay within current_certificates' per-call limit.
    for start in range(0, len(ids), 256):
        result.update(current_certificates(directory, ids[start:start + 256]))
    return result


def _answer(run_dir, question_id, bindings=None, *, replace=False, preview=False,
            _evidence_source=None, _evidence_facts_sha256=None):
    """Read a field catalog or add bindings to current-run certificates.

    An empty replacement clears the question's bindings.
    """
    from agent.answer_projection import catalog, tool_catalog, claim_digest, _path
    planner = Investigation(run_dir)
    with planner._locked():
        state = planner._load()
        if question_id not in {q['id'] for q in state['questions']}:
            raise ValueError('question_id must name a current public question')
        if type(replace) is not bool or type(preview) is not bool:
            raise ValueError('replace and preview must be Booleans')
        path = Path(run_dir) / FILENAME
        document = _document(path, state)
        if bindings is None:
            if replace:
                raise ValueError('replace requires a bindings list')
            from agent.answer_requirements import inspect
            fields = catalog()
            question = next(q for q in state['questions'] if q['id'] == question_id)
            return {'question_id': question_id, 'field_catalog': tool_catalog(),
                    'field_requirements': inspect(question.get('answer_schema', {}), fields['forms'], require_claim_requirements=True, require_evidence_scope=True),
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
            _path(row.get('path'))
            if (not isinstance(row.get('field'), str) or not row['field']
                    or type(row['part']) is not int or row['part'] < 0):
                raise ValueError('binding requires a field name and nonnegative integer part')
            prepared.append(row)
        certificates = _certificates(run_dir, prepared)
        for row in prepared:
            digest = claim_digest(certificates[row['candidate_id']]['claim'])
            if row.get('claim_sha256', digest) != digest:
                raise ValueError('binding hash differs from the recorded claim')
            row['claim_sha256'] = digest
        combined = [b for b in document['bindings'] if not replace or b.get('question_id') != question_id]
        retained_count = len(combined)
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
        digest = _evidence_context(run_dir, state, document, certificates, _evidence_source, _evidence_facts_sha256)
        projection = _project(state, document, certificates, evidence_facts_sha256=digest)
        valid = not projection.get('unsupported') and not projection.get('conflicts')
        if preview:
            return {'preview': True, 'valid': valid, 'persisted': False, 'projection': projection}
        supported_new = any(leaf.get('binding_index', -1) >= retained_count
                            for leaf in projection.get('leaves', []))
        if not valid and (replace or projection.get('conflicts') or not supported_new):
            return dict(projection, valid=False, persisted=False, update_outcome='rejected')
        atomic_json(path, document)
        atomic_json(Path(run_dir) / 'projected-answers.json', projection)
        if not valid:
            return dict(projection, valid=False, persisted=True, update_outcome='partial')
        return projection


def answer(run_dir, question_id, bindings=None, *, replace=False, preview=False,
           _evidence_source=None, _evidence_facts_sha256=None):
    """Inspect or bind fields. A preview or an invalid replacement leaves saved answers unchanged."""
    try:
        return _answer(run_dir, question_id, bindings, replace=replace, preview=preview,
                       _evidence_source=_evidence_source, _evidence_facts_sha256=_evidence_facts_sha256)
    except (ValueError, KeyError, TypeError) as error:
        if preview is True:
            return {'preview': True, 'valid': False, 'persisted': False,
                    'errors': [{'reason': str(error)}]}
        raise


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
    digest = _evidence_context(directory, state, document, certificates)
    run['answer_projection'] = _project(state, document, certificates, evidence_facts_sha256=digest)
    run['answer_bindings'] = deepcopy(document)
    atomic_json(directory / 'projected-answers.json', run['answer_projection'])
    return run


def _inspection_snapshot(run_dir, question_id, *, _evidence_source=None,
                         _evidence_facts_sha256=None):
    """Read inspection metadata and the projection under one state lock. Nothing is saved."""
    from agent.answer_projection import catalog, tool_catalog
    from agent.answer_requirements import inspect
    directory = Path(run_dir)
    planner = Investigation(directory)
    with planner._locked():
        state = planner._load()
        question = next((row for row in state['questions'] if row['id'] == question_id), None)
        if question is None:
            raise ValueError('question_id must name a current public question')
        document = _document(directory / FILENAME, state)
        certificates = _certificates(directory, document['bindings'])
        digest = _evidence_context(directory, state, document, certificates,
                                   _evidence_source, _evidence_facts_sha256)
        projection = _project(state, document, certificates, evidence_facts_sha256=digest)
        metadata = {'question_id': question_id, 'field_catalog': tool_catalog(),
                    'field_requirements': inspect(question.get('answer_schema', {}), catalog()['forms'],
                                                  require_claim_requirements=True, require_evidence_scope=True),
                    'bindings': deepcopy([b for b in document['bindings']
                                          if b.get('question_id') == question_id])}
        return {'inspection': metadata, 'projection': projection}


def read_projection(run_dir):
    """Recompute a bound answer snapshot for coverage diagnostics."""
    directory = Path(run_dir)
    path = directory / FILENAME
    if not path.exists() and not path.is_symlink():
        return None
    planner = Investigation(directory)
    with planner._locked():
        state = planner._load()
        document = _document(path, state)
        certificates = _certificates(directory, document['bindings'])
        digest = _evidence_context(directory, state, document, certificates)
        return _project(state, document, certificates, evidence_facts_sha256=digest)


def project_bundle(run, public, *, authority='recorded_certificates', evidence_facts_sha256=None):
    """Recompute typed answers from bundled claims.

    This checks bindings, not Lean proofs: verify the certificates first.
    """
    from agent.answer_projection import project_answers
    document = run.get('answer_bindings')
    state = run.get('investigation', {})
    projection_public = public
    if document is None:
        document = {'schema_version': 1, 'case_id': public['case_id'],
                    'facts_sha256': state.get('facts_sha256'), 'bindings': []}
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
    recorded = run.get('run_manifest', {}).get('inputs', {}).get('facts', {}).get('sha256')
    declared = [document.get('facts_sha256'), state.get('facts_sha256'), recorded]
    if any(value is not None for value in declared) and len(set(declared)) != 1:
        raise ValueError('bundled answer evidence digest differs across recorded bindings')
    if authority == 'independently_replayed':
        if _scoped(projection_public, document['bindings']) and evidence_facts_sha256 is None:
            raise ValueError('source-scoped replay requires the actual verified facts SHA-256')
        if evidence_facts_sha256 is not None and declared[0] is not None and evidence_facts_sha256 != declared[0]:
            raise ValueError('replayed evidence differs from the bound answer evidence')
    else:
        if evidence_facts_sha256 is not None and evidence_facts_sha256 != recorded:
            raise ValueError('provided evidence digest differs from recorded manifest')
        evidence_facts_sha256 = recorded
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
                           admitted_ids=set(certificates), authority=authority, require_claim_requirements=True,
                           require_evidence_scope=True, evidence_facts_sha256=evidence_facts_sha256)


def report_projection(run):
    """Validate the saved view against its bound fields before showing it as such."""
    try:
        result = project_bundle(run, public_profile(run.get('investigation', {})))
        if result != run.get('answer_projection'):
            raise ValueError('saved answer projection differs from its claim bindings')
        return result, None
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        return None, str(error)
