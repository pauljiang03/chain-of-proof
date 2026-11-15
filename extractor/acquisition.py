"""Device identity of an image; an E01 `sn` counts only for removable, non-optical captures."""
from __future__ import annotations

import json
from pathlib import Path

from . import optical


def scoped_identity(image: str, exhibit: str) -> str:
    """An identity scoped to this evidence set, never a hardware serial."""
    return "image-scoped device " + json.dumps([str(image), str(exhibit)], separators=(",", ":"))


def fallback(image: str, exhibit: str) -> dict:
    return {"device_identity": scoped_identity(image, exhibit),
            "device_identity_kind": "exhibit_image",
            "device_identity_source": "image/exhibit scope; hardware serial unknown",
            "hardware_serial": None, "is_optical": None}


def _serial(value) -> str:
    if not isinstance(value, str) or any(ord(c) < 32 for c in value):
        return ""
    value = value.strip()
    return "" if value.lower() in ("", "unknown", "n/a", "none") else value


def resolve(path, exhibit: dict, manifest_source: str = "explicit acquisition manifest") -> dict:
    """Device identity for one image; conflicting serials withhold the hardware identity."""
    path = Path(path)
    result = fallback(path.name, exhibit.get("exhibit", path.name))
    header, notes = {}, []
    try:
        with path.open("rb") as fh:
            if fh.read(8) in optical.EWF_MAGIC:
                header = optical.ewf_header(fh)
    except Exception as err:
        notes.append(f"acquisition header unavailable: {type(err).__name__}: {err}")
    # Keep the raw header fields as provenance only.
    result["acquisition_header"] = {k: header[k] for k in ("_section", "md", "sn", "l") if k in header}
    try:
        result["is_optical"] = optical.is_optical(path)
    except Exception as err:
        notes.append(f"image type unavailable: {type(err).__name__}: {err}")
    model = str(header.get("md", "")).upper()
    optical_drive = any(label in model for label in ("DVD", "CD-ROM", "CD-RW", "BD-ROM", "BD-RE", "BD-R"))
    if exhibit.get("role") != "removable" or result["is_optical"] or optical_drive:
        notes.append("capture is not an identified removable non-optical device; header serial is not a disc identity")
    else:
        supplied, recorded = _serial(exhibit.get("device_serial")), _serial(header.get("sn"))
        if supplied and recorded and supplied != recorded:
            notes.append("manifest and E01 acquisition serials conflict; hardware identity withheld")
        elif supplied:
            result.update(device_identity=supplied, device_identity_kind="hardware_serial",
                          hardware_serial=supplied, device_identity_source=manifest_source)
        elif recorded and result["is_optical"] is False:
            result.update(device_identity=recorded, device_identity_kind="hardware_serial",
                          hardware_serial=recorded,
                          device_identity_source=f"{path.name}: E01 {header.get('_section', 'header')} sn field (acquisition metadata)")
        else:
            notes.append("no supported hardware serial in acquisition evidence")
    result["identity_notes"] = notes
    return result


def provenance(identity: dict) -> dict:
    return {k: identity[k] for k in ("device_identity", "device_identity_kind", "device_identity_source",
                                    "hardware_serial", "acquisition_header", "identity_notes") if k in identity}


def area(identity: dict) -> str:
    return "unallocated space of device " + identity["device_identity"]
