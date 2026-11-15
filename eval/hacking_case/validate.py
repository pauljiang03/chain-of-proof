"""Read-only Hacking Case contract/source validation; no system output grading."""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import tempfile

from agent.case import read_question_profile
from agent.answer_requirements import KEY, parse as parse_requirement
from eval.benchmark import validate_reference
from eval.key_audit import audit, leaves, pointer, source_span


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts, self.ignore = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.ignore += 1
        if tag in ("br", "p", "h1", "h2", "div"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.ignore = max(0, self.ignore - 1)
        if tag in ("p", "h1", "h2", "div"):
            self.parts.append("\n")

    def handle_data(self, text):
        if not self.ignore:
            self.parts.append(text)


def public_prompts(html):
    parser = _Text()
    parser.feed(html)
    text = "".join(parser.parts)
    start = text.index("1. What is the image hash?")
    section = text[start:text.index("Answers", start)]
    pieces = re.split(r"(?m)^\s*(\d+)\.\s*", section)
    return {"Q" + pieces[i]: " ".join(pieces[i + 1].split())
            for i in range(1, len(pieces), 2)}


def _same(actual, expected):
    return type(actual) is type(expected) and actual == expected


def _literal(lines, binding):
    value = binding.get("literal")
    if not isinstance(value, str) or not value or value not in source_span(lines, binding):
        raise ValueError("source literal absent from its declared span")
    return value


def transform(binding, lines, source_dir):
    """Reproduce only explicitly declared representation operations."""
    operation = binding["operation"]
    if operation == "join_literals":
        return "".join(_literal(lines, part) for part in binding["parts"])
    if operation == "external_literal":
        name = binding.get("source_file")
        if name != "SCHARDT.LOG":
            raise ValueError("unsupported external source")
        return _literal((source_dir / name).read_text().splitlines(), binding)
    raw = _literal(lines, binding)
    if operation == "yes_no":
        if raw not in ("Yes", "No"):
            raise ValueError("expected explicit Yes/No source token")
        return raw == "Yes"
    if operation == "decimal_integer":
        if not re.fullmatch(r"0|[1-9][0-9]*", raw):
            raise ValueError("expected unsigned source decimal")
        return int(raw)
    if operation == "remove_equals":
        context = source_span(lines, {"start_line": binding["context_start_line"],
                                      "end_line": binding["context_end_line"]})
        if "there are no equal signs in the image files" not in context.replace("\n", " "):
            raise ValueError("missing public name-display convention")
        return raw.replace("=", "")
    if operation == "mac_colons":
        if not re.fullmatch(r"[0-9A-Fa-f]{12}", raw):
            raise ValueError("expected twelve hexadecimal MAC digits")
        return ":".join(raw[i:i + 2] for i in range(0, 12, 2))
    if operation == "expand_ms_prefix":
        if not raw.startswith("MS "):
            raise ValueError("expected literal MS product prefix")
        return "Microsoft " + raw[3:]
    if operation == "program_product_name":
        label = raw.split(" (", 1)[0]
        return re.split(r"\s+v(?=\d)", label, maxsplit=1)[0]
    if operation == "cross_question_literal":
        _literal(lines, {"literal": binding["raw_label"],
                         "start_line": binding["raw_start_line"],
                         "end_line": binding["raw_end_line"]})
        if not binding.get("note"):
            raise ValueError("cross-question convention needs a stated reason")
        return raw
    if operation == "local_display_timestamp":
        offset = _literal(lines, {"literal": binding["offset_literal"],
                                 "start_line": binding["offset_start_line"],
                                 "end_line": binding["offset_end_line"]})
        match = re.search(r"\(([+-])(\d{2})hrs GMT\)", offset)
        if not match:
            raise ValueError("source display offset is not explicit")
        hours = int(match[2]) * (1 if match[1] == "+" else -1)
        parsed = datetime.strptime(raw, "%m/%d/%y %I:%M:%S%p")
        return parsed.replace(tzinfo=timezone(timedelta(hours=hours))).isoformat()
    raise ValueError("unsupported source transformation")


def _schema(value, schema):
    kind = schema.get("type")
    matches = {"object": type(value) is dict, "array": type(value) is list,
               "string": type(value) is str, "boolean": type(value) is bool,
               "integer": type(value) is int}
    if not matches.get(kind, False):
        raise ValueError("reference value does not fit its public type")
    if kind == "object":
        properties = schema["properties"]
        if set(value) != set(schema["required"]) or set(value) != set(properties):
            raise ValueError("reference/public required fields differ")
        for name, child in value.items():
            _schema(child, properties[name])
    elif kind == "array":
        for child in value:
            _schema(child, schema["items"])
    elif kind == "integer" and value < schema.get("minimum", value):
        raise ValueError("reference count is outside its public range")
    if KEY in schema:
        parse_requirement(schema[KEY])


def _strings(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"expected", "field_sources", "transformations", "source_document"}:
                raise ValueError("private field in public profile")
            yield from _strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _strings(child)
    elif isinstance(value, str):
        yield value


def validate(reference=None, public=None, *, package=HERE, require_annotations=True):
    """Return source/contract checks; errors identify fields without printing key values."""
    package = Path(package)
    reference = deepcopy(reference) if reference is not None else json.loads((package / "reference.json").read_text())
    public = deepcopy(public) if public is not None else read_question_profile(package / "questions.json")
    with tempfile.TemporaryDirectory(prefix="cop-hacking-public-") as temp:
        path = Path(temp) / "questions.json"
        path.write_text(json.dumps(public))
        read_question_profile(path)
    validate_reference(reference)
    ids = [f"Q{i}" for i in range(1, 32)]
    if reference["case_id"] != "nist-cfreds-hacking" or public["case_id"] != reference["case_id"]:
        raise ValueError("wrong Hacking Case identity")
    if [q["id"] for q in reference["questions"]] != ids or [q["id"] for q in public["questions"]] != ids:
        raise ValueError("all 31 official question IDs must be retained in order")
    manifest = json.loads((package / "sources/manifest.json").read_text())
    for file in manifest["files"]:
        path = Path(file["path"])
        if path.is_absolute() or ".." in path.parts or path.parts[:1] != ("sources",):
            raise ValueError("unsafe source snapshot path")
        actual = package / path
        if actual.is_symlink() or digest(actual) != file["sha256"] or actual.stat().st_size != file["bytes"]:
            raise ValueError("source snapshot hash/size differs")
    html = (package / "sources/Hacking_Case.html").read_text()
    prompts = public_prompts(html)
    transcript = (package / "sources/questions.txt").read_text()
    if transcript != "\n".join(f"{i}. {prompts[f'Q{i}']}" for i in range(1, 32)) + "\n":
        raise ValueError("public question transcript differs from the HTML")
    public_source = reference["public_source"]
    if (public_source["html_sha256"] != digest(package / "sources/Hacking_Case.html")
            or public_source["questions_sha256"] != digest(package / "sources/questions.txt")):
        raise ValueError("public source hash binding differs")
    extras = reference.get("additional_sources", [])
    if (len(extras) != 1 or extras[0].get("id") != "acquisition_notes"
            or extras[0].get("sha256") != digest(package / "sources/SCHARDT.LOG")):
        raise ValueError("acquisition-note source binding differs")
    bound = deepcopy(reference)
    bound["source_document"]["pdf_path"] = str(package / "sources/TestAnswers.pdf")
    source_audit = audit(bound, package / "sources/TestAnswers.txt")
    if not source_audit["source_binding_passed"]:
        raise ValueError("private source-span/literal audit failed")
    lines = (package / "sources/TestAnswers.txt").read_text().splitlines()
    checked, annotations = [], 0
    for q, p in zip(reference["questions"], public["questions"]):
        if q["prompt"] != prompts[q["id"]] or p["prompt"] != q["prompt"] or p["match"] != q["match"]:
            raise ValueError("public/private prompt or matching rule differs: " + q["id"])
        source = q["public_source"]
        raw = source_span(transcript.splitlines(), source)
        if hashlib.sha256(raw.encode()).hexdigest() != source["sha256"]:
            raise ValueError("public prompt source binding differs: " + q["id"])
        expected = q.get("expected")
        if "expected" not in q:
            if q["evaluation"]["status"] != "unevaluable":
                raise ValueError("scorable question lacks its source answer")
            continue
        _schema(expected, p["answer_schema"])
        covered = {b["pointer"] for b in q["field_sources"]}
        for item in q["transformations"]:
            location = item["pointer"]
            if location in covered:
                raise ValueError("duplicate field derivation: " + q["id"] + location)
            if not _same(pointer(expected, location), transform(item, lines, package / "sources")):
                raise ValueError("source transformation differs: " + q["id"] + location)
            covered.add(location)
        if covered != set(leaves(expected)):
            raise ValueError("an expected field has no source binding: " + q["id"])
        for item in q.get("source_role_bindings", []):
            span = source_span(lines, item)
            if item["source_key"] + "=" not in span or item["pointer"] not in covered:
                raise ValueError("source setting-role binding differs: " + q["id"])
        def check_nodes(node):
            nonlocal annotations
            if node.get("type") == "object":
                for child in node["properties"].values():
                    check_nodes(child)
            elif node.get("type") == "array":
                check_nodes(node["items"])
            elif KEY not in node:
                if require_annotations:
                    raise ValueError("unannotated exact answer leaf: " + q["id"])
            else:
                parse_requirement(node[KEY])
                annotations += 1
        check_nodes(p["answer_schema"])
        checked.append({"id": q["id"], "source_bindings": len(covered),
                        "transformations": len(q["transformations"]),
                        "evaluation_status": q["evaluation"]["status"]})
    public_text = "\n".join(_strings(public)).casefold()
    original_text = " ".join(public_prompts(html).values()).casefold() + html.casefold()
    structural = {"server", "user", "email", "nick", "anick"}
    for q in reference["questions"]:
        for location in leaves(q.get("expected")):
            value = pointer(q.get("expected"), location)
            if (isinstance(value, str) and len(value) >= 4 and value.casefold() not in original_text
                    and value not in structural and value.casefold() in public_text):
                raise ValueError("private answer string leaked to public profile: " + q["id"] + location)
    for token in ("TestAnswers", "reference.json", "leakage-answers", "benchmark_nist"):
        if token.casefold() in public_text:
            raise ValueError("private source locator in public profile")
    return {"schema_version": 1, "case_id": reference["case_id"], "passed": True,
            "questions": checked, "question_count": len(checked), "annotated_answer_leaves": annotations,
            "canonical_reference_sha256": hashlib.sha256(json.dumps(reference, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest(),
            "reference_file_sha256": digest(package / "reference.json"),
            "public_profile_file_sha256": digest(package / "questions.json"),
            "validator_sha256": digest(Path(__file__)),
            "source_binding_passed": source_audit["source_binding_passed"],
            "source_snapshot_files_checked": len(manifest["files"]),
            "no_expected_value_leak_check_passed": True,
            "system_accuracy_measured": False, "independent_semantic_review": False,
            "scope": "Source-byte binding, declared transformations, public/private contract symmetry and leakage checks only. Not proof of English interpretation, procedure execution, source authenticity or key truth."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, help="optional new audit file; never overwrite")
    args = parser.parse_args()
    result = validate()
    if args.out:
        with args.out.open("x") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")
    print(json.dumps(result, indent=2))
