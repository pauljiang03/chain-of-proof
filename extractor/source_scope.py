"""Source origin fields (snapshot and variant) for records; missing origins stay unknown."""
from uuid import UUID


def base_volume_scope():
    """Use only at a read site known to address the examined base filesystem."""
    return {'source_snapshot': 'base-volume', 'source_variant': 'primary'}


def vss_snapshot(copy_id):
    """Canonical identity for an explicitly selected VSS store."""
    if not isinstance(copy_id, (str, UUID)):
        raise ValueError('VSS source identity must be a UUID')
    try:
        value = UUID(str(copy_id))
    except (ValueError, AttributeError) as error:
        raise ValueError('VSS source identity must be a UUID') from error
    return 'vss:' + str(value)


def merge_scope(common, details=None):
    """Merge provenance without replacing a specific origin by a default."""
    result = dict(common)
    result.update(details or {})
    for key in ('source_snapshot', 'source_variant'):
        value = result.get(key)
        if not isinstance(value, str) or not value.strip():
            result[key] = 'unknown'
        elif key == 'source_snapshot' and value.startswith('vss:'):
            try:
                result[key] = vss_snapshot(value[4:])
            except ValueError:
                result[key] = 'unknown'
    return result


def subject_scope(provenance):
    """Origin fields to include in a subject identity."""
    resolved = merge_scope(provenance)
    return [resolved.get('image'), resolved.get('exhibit'),
            resolved['source_snapshot'], resolved['source_variant']]
