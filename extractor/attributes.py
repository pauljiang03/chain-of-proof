"""Emit typed observations from a source artifact, without drawing conclusions."""
import hashlib
import json
import re

from checker.catalog import ROLES


def emit_attribute(ev, subject, role, value, observed_at_us, **provenance):
    """Emit one subject/role/value observation; `t` is the examination time, not an event time."""
    if not isinstance(subject, str) or not subject.strip():
        raise ValueError('attribute subject must be a nonempty scoped identity')
    if role not in ROLES:
        raise ValueError('attribute role is not in the reviewed catalog')
    spec = ROLES[role]
    expected = {'string': str, 'integer': int, 'signed_integer': int, 'boolean': bool}[spec.value_type]
    if type(value) is not expected or (spec.value_type == 'integer' and value < 0):
        raise ValueError('attribute value must have its declared native type (integer count roles are nonnegative)')
    if type(observed_at_us) is not int or observed_at_us <= 0:
        raise ValueError('attribute examination timestamp must be positive UTC microseconds')
    if not isinstance(provenance.get('artifact'), str) or not provenance['artifact']:
        raise ValueError('attribute provenance must name its source artifact')
    if role.startswith('image.'):
        length = {'md5': 32, 'sha1': 40, 'sha256': 64}[role.rsplit('.', 1)[1]]
        if not re.fullmatch('[0-9a-f]{' + str(length) + '}', value):
            raise ValueError('image digest must be canonical lowercase hexadecimal')
    # Store values as JSON, so empty text ("") stays distinct from the store's empty sentinel.
    encoded = json.dumps(value, ensure_ascii=True)
    identity = 'attribute:' + hashlib.sha256(json.dumps(
        [subject, role, value, observed_at_us, provenance], sort_keys=True,
        separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()).hexdigest()
    prov = dict(provenance, attribute_role=role, attribute_value_type=spec.value_type,
                timestamp_semantics='examination_observation',
                time_meaning='when this source attribute was examined, not the described event')
    for kind, item in (('attributeSubject', subject), (spec.kind, role), (spec.value_kind, encoded)):
        ev.add(kind, observed_at_us, 1, identity, item, **prov)
    return identity
