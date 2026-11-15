"""Emit typed source observations without converting them into forensic conclusions."""
import hashlib
import json
import re

from checker.catalog import ROLES


def emit_attribute(ev, subject, role, value, observed_at_us, **provenance):
    """Emit one linked subject/role/typed-value triple; return its stable identity.

    ``subject`` must be scoped to the evidence and source/object. Provenance must
    identify the source artifact and its field/byte/key locator where available.
    The triple timestamp is examination time. An event timestamp is a separate
    typed attribute value; no event-time inference comes from this row's ``t``.
    """
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
    # Quoted strings preserve real empty text despite the legacy interner's
    # empty-entity sentinel. All value kinds use exact canonical JSON. Only an
    # explicitly reviewed signed_integer role may emit a negative native integer.
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
