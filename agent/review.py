"""Cross-record diagnostics: possible conflicts and ambiguities, never findings.

The scan is capped and no rule joins records pairwise. Two records are the same
observation only with an explicit observation, offset, event-record or row ID; a
shared path, file name or timestamp never suffices.
"""
from __future__ import annotations

from copy import deepcopy

from checker.facts import Fact, KINDS


DISCLAIMER = ('Review diagnostics are unverified prompts for investigation, not Lean claims, '
              'proofs of falsehood, or a choice of which source is true. A clean or truncated review '
              'does not establish that the evidence is consistent or complete.')
LIMITATIONS = [
    'Exact image, exhibit, source and supplied snapshot qualifiers are retained; independent sources are not merged.',
    'Shared labels can name different devices or volumes. Label ambiguity is not a factual contradiction.',
    'Repeated events, file creation/modification pairs, and different timestamp meanings do not establish a contradiction.',
    'Timestamp comparisons preserve supplied uncertainty; overlapping or touching intervals are not flagged.',
    'Observation and event identity depend on parser provenance, which this diagnostic does not verify.',
    'The source.all() interface may materialize the whole store before the bounded scan; an explicit facts iterable avoids that read.',
    'Only recognized, explicitly scoped patterns are reviewed. Missing diagnostics do not establish consistency.',
]
_SCOPE_FIELDS = ('exhibit', 'case_id', 'partition', 'partition_start_sector', 'volume_id',
                 'volume_serial', 'volume_set', 'snapshot_id', 'snapshot', 'view',
                 'filesystem_view', 'vat_sector', 'allocation_table_sector', 'version',
                 'generation', 'session', 'track', 'account', 'user', 'profile')
_VALUE_KINDS = frozenset(('systemSetting', 'fileContent', 'lnkTarget'))


def _atom(value):
    return value if (type(value) is int or isinstance(value, str) and value.strip()) else None


def _parts(prov, keys):
    return tuple((key, _atom(prov.get(key))) for key in keys if _atom(prov.get(key)) is not None)


def _row(fact):
    if isinstance(fact, dict):
        row = {name: fact.get(name) for name in ('id', 'kind', 't', 'res', 'obj', 'aux', 'prov')}
    else:
        row = {name: getattr(fact, name, None) for name in ('id', 'kind', 't', 'res', 'obj', 'aux', 'prov')}
    if (not isinstance(row['kind'], str) or row['kind'] not in KINDS or not isinstance(row['prov'], dict)
            or any(type(row[name]) is not int or row[name] < 0 for name in ('id', 't', 'res', 'obj', 'aux'))):
        return None
    return row


def _scope(prov):
    image = prov.get('image')
    return (('image', image),) + _parts(prov, _SCOPE_FIELDS) if isinstance(image, str) and image.strip() else None


def _source(prov):
    artifact = prov.get('artifact')
    if not isinstance(artifact, str) or not artifact.strip():
        return None
    return (('artifact', artifact),) + _parts(prov, ('source_path', 'source_file', 'source', 'browser',
                                                  'profile_path', 'hive_path', 'table', 'channel', 'provider',
                                                  'field', 'value_name', 'property', 'subrecord'))


def _observation(prov):
    source = _source(prov)
    if source is None:
        return None
    # record_id alone can be a URL or a recurring event type, not a unique observation.
    locator = _parts(prov, ('observation_id', 'source_record_id', 'event_record_id', 'byte_offset', 'offset'))
    if not locator and _atom(prov.get('table')) is not None:
        locator = _parts(prov, ('row_id',))
    return source + locator if locator else None


def _meaning(prov):
    result = _parts(prov, ('time_meaning', 'timestamp_semantics'))
    return result or None


def _recorded_event_time(prov):
    semantics = ' '.join(str(value).lower() for _, value in _parts(prov, ('time_meaning', 'timestamp_semantics')))
    return bool(semantics) and 'examin' not in semantics and 'observation time' not in semantics


def _interval(row):
    return max(0, row['t'] - row['res']), row['t'] + row['res']


def review(source, facts=None, *, max_records=500000, max_diagnostics=100):
    """Return bounded, deterministic diagnostics for records in the given order.

    A truncated scan or output is marked; witnesses are examples, not a full group.
    """
    if type(max_records) is not int or not 1 <= max_records <= 1000000:
        raise ValueError('max_records must be an integer from 1 to 1000000')
    if type(max_diagnostics) is not int or not 1 <= max_diagnostics <= 1000:
        raise ValueError('max_diagnostics must be an integer from 1 to 1000')
    source_rows = source.all() if facts is None else facts
    labels, values, times, orders = {}, {}, {}, {}
    emitted, diagnostics = set(), []
    examined = invalid = scoped = 0
    scan_truncated = output_truncated = False

    def text(identifier):
        result = source.string(identifier)
        return result if isinstance(result, str) and result.strip() and result != f'#{identifier}' else None

    def copied(row):
        result = deepcopy(row)
        result.update(obj_text=text(row['obj']), aux_text=text(row['aux']))
        # Recompute only the row binding, not a proof; no certificate is issued.
        result['row_sha256'] = Fact(**row).row_sha256()
        return result

    def emit(category, key, witnesses, summary, why, observed, required):
        nonlocal output_truncated
        marker = (category, key)
        if marker in emitted:
            return
        emitted.add(marker)
        if len(diagnostics) >= max_diagnostics:
            output_truncated = True
            return
        ordered = sorted(witnesses, key=lambda row: row['id'])
        diagnostics.append({'id': f'REV{len(diagnostics) + 1:04d}', 'status': 'diagnostic',
                            'category': category, 'record_ids': [row['id'] for row in ordered],
                            'summary': summary, 'why': why, 'records': [copied(row) for row in ordered],
                            'observed': observed, 'required': required})

    for item in source_rows:
        if examined == max_records:
            scan_truncated = True
            break
        examined += 1
        row = _row(item)
        if row is None:
            invalid += 1
            continue
        prov, scope = row['prov'], _scope(row['prov'])
        if scope is None:
            continue
        scoped += 1
        kind = row['kind']
        if kind in ('volumeSeen', 'lnkTarget', 'volumeOnDevice', 'volumeRecorded'):
            label = text(row['obj']) if kind == 'volumeSeen' else prov.get('volume_label')
            serial = text(row['aux'])
            if isinstance(label, str) and label.strip() and row['aux'] != 0 and serial:
                key = scope, label
                previous = labels.setdefault(key, (serial, row))
                if previous[0] != serial:
                    emit('identity_label_ambiguity', key, [previous[1], row],
                         'One label is associated with different recorded volume identities.',
                         'Exact label text agrees within the same image scope, but the associated identities differ. '
                         'Different devices, reformatted media, or reused labels can legitimately produce this pattern.',
                         {'label': label, 'identities': [previous[0], serial], 'scope': dict(scope)},
                         'Use a serial and independently established device/volume linkage; do not identify a device by label alone.')

        observation, meaning = _observation(prov), _meaning(prov)
        if observation is not None and meaning is not None:
            key = scope, observation, kind, row['obj'], meaning
            aux = text(row['aux'])
            if kind in _VALUE_KINDS and aux is not None:
                previous = values.setdefault(key, (aux, row))
                if previous[0] != aux:
                    emit('same_observation_value_disagreement', key, [previous[1], row],
                         'The same scoped observation assigns different values to one entity.',
                         'Image, source locator, kind, entity and timestamp meaning agree; the single-valued field differs. '
                         'This can indicate a parser, source-version, or identity issue and does not select the true value.',
                         {'values': [previous[0], aux], 'scope': dict(scope), 'observation': dict(observation)},
                         'Inspect the source bytes, field semantics and snapshot identity; retain both records until reconciled.')
            if _recorded_event_time(prov):
                time_key = key, row['aux']
                low, high = _interval(row)
                extreme = times.setdefault(time_key, [row, row])
                max_low, min_high = extreme
                witness = min_high if low > _interval(min_high)[1] else max_low if high < _interval(max_low)[0] else None
                if witness is not None:
                    emit('same_observation_time_disagreement', time_key, [witness, row],
                         'One explicitly identified observation has disjoint recorded time intervals.',
                         'The source observation, entity, related value, kind and timestamp meaning agree. '
                         'The supplied uncertainty intervals do not overlap or touch; independent sources are not joined.',
                         {'intervals_us': [{'record_id': r['id'], 'lower': _interval(r)[0], 'upper': _interval(r)[1]}
                                           for r in (witness, row)], 'scope': dict(scope), 'observation': dict(observation)},
                         'Review raw timestamps, conversion rules, uncertainty and source-version identity; neither timestamp is preferred.')
                if low > _interval(max_low)[0]:
                    extreme[0] = row
                if high < _interval(min_high)[1]:
                    extreme[1] = row

        role, instance, event = prov.get('timestamp_role'), _atom(prov.get('event_instance_id')), _atom(prov.get('event_meaning'))
        origin = _source(prov)
        if role in ('start', 'end') and instance is not None and event is not None and origin is not None:
            key = scope, origin, kind, row['obj'], row['aux'], instance, event
            pair = orders.setdefault(key, {})
            old = pair.get(role)
            if old is None or (role == 'start' and _interval(row)[0] > _interval(old)[0]) or (role == 'end' and _interval(row)[1] < _interval(old)[1]):
                pair[role] = row
            if 'start' in pair and 'end' in pair and _interval(pair['start'])[0] > _interval(pair['end'])[1]:
                start, end = pair['start'], pair['end']
                emit('explicit_event_order_conflict', key, [start, end],
                     'An explicitly scoped event ends before it starts under the supplied uncertainty.',
                     'Both records explicitly identify the same event instance, event meaning, entity and source. '
                     'The latest possible end is earlier than the earliest possible start. No file-lifecycle order was assumed.',
                     {'event_instance_id': instance, 'event_meaning': event,
                      'start_record_id': start['id'], 'start_interval_us': list(_interval(start)),
                      'end_record_id': end['id'], 'end_interval_us': list(_interval(end))},
                     'Inspect the stated event-instance linkage, role meanings, raw timestamps and conversion; do not silently reorder the records.')

    return {'schema_version': 1, 'status': 'diagnostic',
            'scope': {'records_examined': examined, 'records_with_image_scope': scoped,
                      'records_unusable': invalid, 'max_records': max_records,
                      'max_diagnostics': max_diagnostics, 'scan_truncated': scan_truncated,
                      'diagnostics_truncated': output_truncated,
                      'input': 'source_all' if facts is None else 'supplied_subset',
                      'ordering': 'supplied_record_order', 'witnesses': 'two example records per diagnostic'},
            'diagnostics': diagnostics, 'limitations': list(LIMITATIONS), 'disclaimer': DISCLAIMER}
