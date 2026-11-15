"""Check that a reference's answers are bound to spans of its source text.

Checks question spans, field_sources literals and timestamp_derivations.
It does not prove that the reference interprets the source correctly.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def pointer(value, path):
    if path == "":
        return value
    if not isinstance(path, str) or not path.startswith("/"):
        raise ValueError("expected a JSON pointer")
    for part in path[1:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def leaves(value, path=""):
    if isinstance(value, dict) and value:
        return [p for k, v in value.items() for p in leaves(v, path + "/" + k.replace("~", "~0").replace("/", "~1"))]
    if isinstance(value, list) and value:
        return [p for i, v in enumerate(value) for p in leaves(v, path + "/" + str(i))]
    return [path]


def source_span(lines, source):
    start, end = source["start_line"], source["end_line"]
    if (isinstance(start, bool) or isinstance(end, bool) or not isinstance(start, int)
            or not isinstance(end, int) or not 1 <= start <= end <= len(lines)):
        raise ValueError("invalid source line range")
    return "\n".join(lines[start - 1:end]) + "\n"


def utc(value):
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("expected timestamp must have an explicit offset")
    return dt.astimezone(timezone.utc)


def timestamp_conversion(derivation, expected):
    """Validate a declared local-time conversion, rejecting ambiguous DST guesses."""
    local = datetime.fromisoformat(derivation["source_value"])
    if local.tzinfo is not None:
        actual = local.astimezone(timezone.utc)
    else:
        zone = ZoneInfo(derivation["source_timezone"])
        options = []
        for fold in (0, 1):
            aware = local.replace(tzinfo=zone, fold=fold)
            converted = aware.astimezone(timezone.utc)
            if converted.astimezone(zone).replace(tzinfo=None) == local and converted not in options:
                options.append(converted)
        if not options:
            raise ValueError("local time does not exist in the declared timezone")
        if len(options) > 1:
            if derivation.get("fold") not in (0, 1):
                raise ValueError("ambiguous local time requires an explicit fold")
            actual = local.replace(tzinfo=zone, fold=derivation["fold"]).astimezone(timezone.utc)
        else:
            actual = options[0]
    if actual != utc(expected):
        raise ValueError("declared timestamp conversion does not equal expected value")


def audit(reference, source_path):
    raw = Path(source_path).read_bytes()
    lines = raw.decode("utf-8").splitlines()
    document = reference.get("source_document", {})
    errors, questions = [], []
    if document.get("sha256") != digest(raw):
        errors.append("source document SHA-256 differs or is missing")
    pdf_hash = None
    if document.get("pdf_path"):
        pdf = Path(document["pdf_path"])
        if not pdf.is_absolute():
            pdf = ROOT / pdf
        try:
            pdf_hash = digest(pdf.read_bytes())
            if document.get("pdf_sha256") != pdf_hash:
                errors.append("source PDF SHA-256 differs or is missing")
        except OSError as e:
            errors.append(f"source PDF could not be read: {e}")
    ids = set()
    for q in reference.get("questions", []):
        qid = q.get("id")
        issues, bound = [], set()
        if qid in ids:
            errors.append(f"duplicate question ID: {qid}")
        ids.add(qid)
        try:
            span = source_span(lines, q["source"])
            if digest(span.encode()) != q["source"].get("sha256"):
                raise ValueError("question source-span SHA-256 differs or is missing")
        except (ValueError, KeyError, TypeError) as e:
            issues.append(str(e))
        expected = q.get("expected")
        for field in q.get("field_sources", []):
            try:
                value = pointer(expected, field["pointer"])
                span = source_span(lines, field)
                literal = field["literal"]
                if not isinstance(literal, str) or not literal or literal not in span:
                    raise ValueError("declared literal is absent from its source span")
                # Literal equality only, never fuzzy matching.
                if not isinstance(value, str) or value != literal:
                    raise ValueError("literal binding does not equal the expected string")
                bound.add(field["pointer"])
            except (ValueError, KeyError, IndexError, TypeError) as e:
                issues.append(f"field {field.get('pointer')}: {e}")
        conversions = 0
        for conversion in q.get("timestamp_derivations", []):
            try:
                span = source_span(lines, conversion)
                if conversion["source_value"] not in span:
                    raise ValueError("source timestamp is absent from its source span")
                timestamp_conversion(conversion, pointer(expected, conversion["pointer"]))
                bound.add(conversion["pointer"])
                conversions += 1
            except (ValueError, KeyError, IndexError, TypeError) as e:
                issues.append(f"timestamp {conversion.get('pointer')}: {e}")
        questions.append({"id": qid, "source_binding_passed": not issues,
                          "issues": issues, "expected_leaves": len(leaves(expected)),
                          "literally_or_arithmetically_bound_leaves": len(bound),
                          "checked_timestamp_conversions": conversions,
                          "evaluation": q.get("evaluation")})
    if not questions:
        errors.append("reference contains no questions")
    return {"source_sha256": digest(raw), "source_pdf_sha256": pdf_hash, "document_errors": errors,
            "questions": questions, "source_binding_passed": not errors and all(q["source_binding_passed"] for q in questions),
            "review_status": reference.get("review_status", "unspecified"),
            "semantic_correctness": "not_proved",
            "note": "Hashes prove binding to the supplied source text, not faithful interpretation "
                    "or fidelity of PDF-to-text extraction. Literal/declared time conversion checks "
                    "cover only listed fields. Independent review and raw-evidence validation remain necessary."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference")
    parser.add_argument("--source", help="override source_document.path")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    path = Path(args.reference)
    reference = json.loads(path.read_text())
    source = Path(args.source or reference["source_document"]["path"])
    if not source.is_absolute():
        source = ROOT / source
    result = audit(reference, source)
    result["reference_sha256"] = digest(path.read_bytes())
    out = Path(args.out)
    if out.exists():
        parser.error("refusing to overwrite existing audit output")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(f"{len(result['questions'])} source bindings checked; "
          f"binding checks passed: {result['source_binding_passed']}; semantic correctness not proved")
    return 0 if result["source_binding_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
