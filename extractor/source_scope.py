"""Explicit source origins for fresh extraction; never infer them from absence.

Snapshot identifies the filesystem bytes read. Variant identifies primary or
alternate artifact state within that snapshot. Neither identifies a physical user
or asserts that a retained historical record describes the machine's current state.
"""
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
    """Merge provenance without replacing a specific origin with common defaults.

    Missing or malformed scope remains explicitly unknown. This function does not
    upgrade historical facts or infer a primary origin from a missing backup flag.
    """
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
    """Bind typed subjects to the same origin axes as their retained provenance."""
    resolved = merge_scope(provenance)
    return [resolved.get('image'), resolved.get('exhibit'),
            resolved['source_snapshot'], resolved['source_variant']]
