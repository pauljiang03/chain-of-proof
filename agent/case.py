"""Public case context, kept separate from evidence and private scoring references."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional, Tuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FACTS = ROOT / "evidence" / "case_facts.json"
LEGACY_NAME = "NIST CFReDS Data Leakage Case"


@dataclass(frozen=True)
class CaseProfile:
    name: str
    brief: str
    questions: Tuple[str, ...]
    time_zone: Optional[str] = None

    def public_dict(self) -> dict:
        return asdict(self)


LEGACY_PROFILE = CaseProfile(
    name=LEGACY_NAME,
    brief="You are the investigator on a suspected data-leak case.\n\nTHE CASE\n'Iaman Informant' (Windows account `informant`) is a manager at a technology company.\nHe is suspected of leaking confidential files about a secret project to 'Spy\nConspirator', who works for a competitor. Company policy: confidential files may be kept\nonly on authorized external storage and on the secured network drive, and personal\nstorage devices are forbidden. He was stopped at the security checkpoint carrying a USB\nmemory stick and a CD. Four things were seized and imaged: his work PC, a company-issued\nUSB stick (exhibit RM#1), his own USB stick (RM#2) and a CD-R (RM#3).\n\nDeterministic tools extracted records from those images into one table. Not everything\nhas been extracted yet. If the records needed for a question are missing, say so. Do\nnot guess.",
    questions=('The machine and its users: what system is it, which accounts exist, who used it and when?', 'External storage: which devices were attached, when, and what does each hold now?', 'Programs: what was installed or run in the period that could move data out or remove traces?', 'The web: what was searched for, visited and downloaded?', 'E-mail and cloud storage: which messages were exchanged, which accounts and file events did a cloud client record?', 'Files: which confidential files were opened and from where (network drive, each device, the disc)? What was created, copied, renamed or deleted on each device, including records recovered from formatted media? Which copies have identical content?', 'The disc: what is on it, and when was it written?', 'Covering tracks: what was deleted, wiped, cleaned or uninstalled, and when?', 'The story: in what order did the key events happen, and how did confidential data leave the company?'),
    time_zone="America/New_York",
)

GENERIC_QUESTIONS = (
    "What systems, users and accounts are recorded, and what can be established about their activity?",
    "Which storage devices and volumes are recorded, and how are they linked to files?",
    "What program, web, message and cloud activity bears on the supplied case brief?",
    "What file contents and file operations are supported by the available records?",
    "What order of relevant events can be certified, accounting for timestamp uncertainty?",
    "Which questions remain unresolved, and which missing records or unsupported forms prevent an answer?",
)
GENERIC_BRIEF = (
    "You are investigating the supplied digital evidence. Use the public case context "
    "and the records to establish relevant activity. No case-specific allegation, person, "
    "device assignment or company policy has been supplied. Deterministic tools extracted "
    "the records; extraction may be incomplete. State what the records support and what "
    "cannot be established. Do not guess."
)


def _text(value, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a nonempty string")
    return value.strip()


def validate_zone(value) -> Optional[str]:
    if value is None:
        return None
    zone = _text(value, "time_zone")
    try:
        ZoneInfo(zone)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(f"time_zone must be a valid IANA timezone: {zone!r}") from exc
    return zone


def read_profile(path: Path) -> CaseProfile:
    """Accept public context only. Reference paths, answers and arbitrary metadata are rejected.

    The caller is responsible for supplying a genuinely public brief: a schema cannot
    determine whether a free-text string contains a private answer.
    """
    data = json.loads(Path(path).read_text())
    if not isinstance(data, dict):
        raise ValueError("case profile must be a JSON object")
    extra = set(data) - {"name", "brief", "questions", "time_zone"}
    if extra:
        raise ValueError("case profile contains unsupported fields: " + ", ".join(sorted(extra)))
    questions = data.get("questions")
    if not isinstance(questions, list) or not questions:
        raise ValueError("questions must be a nonempty list of public question strings")
    return CaseProfile(
        name=_text(data.get("name"), "name"),
        brief=_text(data.get("brief"), "brief"),
        questions=tuple(_text(q, "question") for q in questions),
        time_zone=validate_zone(data.get("time_zone")),
    )


def evidence_metadata(facts_path: Path) -> dict:
    """The JSON extractor's public metadata. The DuckDB schema has no case metadata."""
    if facts_path.suffix.lower() != ".json":
        return {}
    data = json.loads(facts_path.read_text())
    meta = data.get("_meta", {})
    return meta if isinstance(meta, dict) else {}


def select_case(facts_path: Path, profile_path: Optional[Path] = None,
                default_facts: Path = DEFAULT_FACTS) -> Tuple[CaseProfile, str]:
    """Return a profile and its provenance. Only the original default gets legacy context.

    Metadata supplies a case name and timezone, never allegations or questions. A copied
    or regenerated evidence file must opt into any case-specific public brief explicitly.
    """
    if profile_path is not None:
        return read_profile(profile_path), "profile"
    meta = evidence_metadata(facts_path)
    name = meta.get("case") or meta.get("name")
    if isinstance(name, dict):
        name = name.get("name")
    if facts_path.resolve() == default_facts.resolve() and name == LEGACY_NAME:
        return LEGACY_PROFILE, "legacy"
    pc = meta.get("pc")
    pc = pc if isinstance(pc, dict) else {}
    zone = meta.get("time_zone") or pc.get("time_zone") or meta.get("fat_time_zone")
    return CaseProfile(
        name=_text(name, "metadata case name") if name is not None else "Digital evidence investigation",
        brief=GENERIC_BRIEF,
        questions=GENERIC_QUESTIONS,
        time_zone=validate_zone(zone),
    ), "metadata" if name is not None or zone is not None else "generic"

