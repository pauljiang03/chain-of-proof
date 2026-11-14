"""Literal Markdown values and finding-scoped evidence/proof anchors."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import re
import string
import unicodedata


def text(value) -> str:
    """Render untrusted text literally, without Markdown/HTML links or markup.

    Character references are decoded as text after Markdown syntax is parsed.
    Control characters are shown as escapes so metadata cannot add report blocks.
    """
    raw = str(value)
    visible = "".join(f"\\u{ord(c):04x}" if unicodedata.category(c) in {"Cc", "Cf"} else c
                      for c in raw)
    return "".join(f"&#{ord(c)};" if c in string.punctuation else c for c in visible)


def json_text(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2)


def fenced(value: str, language: str = "") -> str:
    """A copied proof cannot terminate its own fence and inject report content."""
    size = max([3] + [len(m[0]) + 1 for m in re.finditer(r"`+", value)])
    fence = "`" * size
    return f"{fence}{language}\n{value}\n{fence}"


def anchor(name: str) -> str:
    # Callers pass ordinal identifiers, never a finding or fact ID from input.
    if not re.fullmatch(r"(?:evidence-f\d+-r\d+|proof-f\d+)", name):
        raise ValueError("report anchor must be generated from finding/row ordinals")
    return f'<a id="{name}"></a>'


def value(mapping, key) -> str:
    return text(mapping[key]) if key in mapping else "Not recorded"


def recorded_time(fact) -> str:
    stamp = fact.get("t")
    if not isinstance(stamp, int) or isinstance(stamp, bool):
        return value(fact, "t")
    try:
        iso = (datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=stamp)).isoformat()
    except (OverflowError, ValueError):
        return text(stamp) + " microseconds (outside displayable datetime range)"
    return text(iso.replace("+00:00", "Z")) + f" ({stamp} microseconds since the Unix epoch)"


def conflicting_fact_ids(findings) -> set:
    copies = {}
    for finding in findings:
        for fact in finding.get("cited_facts", []):
            identity = json_text(fact.get("id"))
            copies.setdefault(identity, set()).add(json_text(fact))
    return {identity for identity, variants in copies.items() if len(variants) > 1}


def evidence_record(finding, fact, finding_number, row_number, conflicts) -> list:
    target = f"evidence-f{finding_number}-r{row_number}"
    prov = fact.get("prov") if isinstance(fact.get("prov"), dict) else {}
    lines = [anchor(target), "", f"### Fact {value(fact, 'id')} — finding {value(finding, 'finding_id')}", ""]
    if json_text(fact.get("id")) in conflicts:
        lines += ["**Conflicting copied rows share this fact ID.** They are shown separately; "
                  "this report does not resolve the conflict.", ""]
    lines += [f"- Kind: {value(fact, 'kind')}",
              f"- Image: {value(prov, 'image')}; exhibit: {value(prov, 'exhibit')}",
              f"- Artifact: {value(prov, 'artifact')}",
              f"- Extracted object: {value(fact, 'obj_text')} (interned ID {value(fact, 'obj')})",
              f"- Related value: {value(fact, 'aux_text')} (interned ID {value(fact, 'aux')})",
              f"- Recorded timestamp: {recorded_time(fact)}",
              f"- Timestamp meaning: {value(prov, 'time_meaning')}",
              f"- Timestamp uncertainty: {value(fact, 'res')} microseconds",
              f"- Parser: {value(prov, 'parser')}; tool: {value(prov, 'tool')}",
              f"- Row SHA-256: {value(fact, 'row_sha256')}", "",
              "Copied provenance, including any supplied source locations:", "",
              fenced(json_text(fact.get("prov")), "json") if "prov" in fact else "Not recorded.", ""]
    return lines


def proof_record(finding, number) -> list:
    lines = [anchor(f"proof-f{number}"), "", f"### Proof for {value(finding, 'finding_id')}", "",
             f"Trust tier: {value(finding, 'trust_tier')}. Declared axioms: {value(finding, 'axioms')}.", ""]
    if "claim" in finding:
        lines += ["Declared claim:", "", fenced(json_text(finding["claim"]), "json"), ""]
    lean = finding.get("lean")
    if isinstance(lean, str) and lean.strip():
        lines += ["Embedded Lean source (copied, not executed by this renderer):", "", fenced(lean, "lean"), ""]
    else:
        lines += ["Embedded Lean source was not included in this bundle. No filesystem link is inferred.", ""]
    return lines
