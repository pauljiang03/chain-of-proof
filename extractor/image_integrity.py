"""Hash logical image bytes and retain acquisition digests as separate evidence.

Container-segment hashes bind downloads; they are not hashes of the acquired disk.
This reader streams the complete logical image and emits no digest for an incomplete
read. A matching pair establishes equality of two recorded digests, not authenticity
of the original acquisition or collision resistance of MD5.
"""
from __future__ import annotations

import hashlib
from contextlib import ExitStack, contextmanager
from pathlib import Path

from .optical import EWF_MAGIC, ewf_digests, ewf_segments
from .source_scope import merge_scope

ALGORITHMS = ("md5", "sha1", "sha256")
BLOCK = 4 * 1024 * 1024


def hash_stream(stream, size):
    """Require exactly the advertised logical size, including a check for surplus bytes."""
    if type(size) is not int or size < 0:
        raise ValueError("logical image size must be a nonnegative integer")
    hashes = {algorithm: hashlib.new(algorithm) for algorithm in ALGORITHMS}
    total = 0
    while total < size:
        chunk = stream.read(min(BLOCK, size - total))
        if not chunk or len(chunk) > size - total:
            raise ValueError(f"incomplete logical image: expected {size} bytes, read {total}")
        total += len(chunk)
        for digest in hashes.values():
            digest.update(chunk)
    if stream.read(1):
        raise ValueError("logical image exceeds its advertised size")
    return {algorithm: digest.hexdigest() for algorithm, digest in hashes.items()}


@contextmanager
def logical_stream(path):
    path = Path(path)
    with ExitStack() as stack:
        first = stack.enter_context(path.open("rb"))
        is_ewf = first.read(8) in EWF_MAGIC
        first.seek(0)
        if is_ewf:
            from dissect.evidence import EWF
            segments = ewf_segments(path)
            handles = [stack.enter_context(segment.open("rb")) for segment in segments]
            ewf = EWF(handles)
            yield ewf.open(), ewf.size, segments, "ewf_logical_image"
        else:
            yield first, path.stat().st_size, [path], "raw_image"


def inspect(path):
    """Return full-stream hashes plus checksummed EWF acquisition declarations."""
    with logical_stream(path) as (stream, size, segments, representation):
        actual = hash_stream(stream, size)
        recorded = []
        if representation == "ewf_logical_image":
            for segment in segments:
                with segment.open("rb") as fh:
                    for algorithm, value, section, offset in ewf_digests(fh):
                        recorded.append({"algorithm": algorithm, "digest": value,
                                         "segment": segment.name, "section": section,
                                         "offset": offset})
        # Contradictory declarations are retained, never collapsed to a favorable one.
        comparisons = [{**entry, "recomputed": actual[entry["algorithm"]],
                        "matches": entry["digest"] == actual[entry["algorithm"]]}
                       for entry in recorded]
        return {"logical_bytes": size, "representation": representation,
                "computed": actual, "recorded": recorded, "comparisons": comparisons,
                "segments": [p.name for p in segments]}


def extract(ev, path, ctx):
    from .attributes import emit_attribute
    result = inspect(path)
    common = merge_scope(ctx["common"], dict(artifact="complete logical image byte stream",
                  reader="image_integrity", logical_bytes=result["logical_bytes"],
                  representation=result["representation"], segments=result["segments"],
                  source_snapshot="evidence-image", source_variant="logical-image",
                  timestamp_semantics="examination_observation",
                  scope="Digest equality does not establish acquisition authenticity."))
    # Both roles describe the same image entity, from different byte sources.
    subject = f"{ctx['common']['exhibit']}:{ctx['common']['image']}:logical-image"
    for algorithm, value in result["computed"].items():
        emit_attribute(ev, subject, f"image.logical.{algorithm}", value,
                       ctx["examined_at"], **common)
    for entry in result["recorded"]:
        emit_attribute(ev, subject, f"image.acquisition.{entry['algorithm']}", entry["digest"],
                       ctx["examined_at"], **dict(common, artifact=entry["segment"],
                       source_variant="acquisition-container",
                       section=entry["section"], byte_offset=entry["offset"],
                       scope="Digest declared by the acquisition container, not independently authenticated."))
    if not result["recorded"]:
        ev.problem(f"image integrity {Path(path).name}", ValueError(
            "no acquisition digest is stored in this image; only recomputed hashes are available"))
