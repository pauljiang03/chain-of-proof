"""Answer public NIST question contracts from an already verified saved run.

No answer key or benchmark reference is read. The adapter exports supported fields
and leaves other fields absent/questions unknown. It does not prove completeness,
intent, absence of activity, or every semantic interpretation of hashed provenance.

    python -m eval.nist_answers --run runs/dev/combined-reviewed/run.json \
        --questions eval/benchmark_nist_questions.json --out /path/new-answers.json
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import ipaddress
import json
from pathlib import Path, PureWindowsPath
import re
from zoneinfo import ZoneInfo

from checker import claims


VERSION = "1.2"


def utc(us):
    return (datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=us)).isoformat().replace("+00:00", "Z")


def normalized_path(value):
    value = str(value)
    if value.startswith("\\??\\"):
        value = value[4:]
    if re.match(r"^\\[A-Za-z]:\\", value):
        value = value[1:]
    return value.rstrip("\\/")


def concrete_path(value):
    """An aggregate artifact glob is not an observed filename."""
    return isinstance(value, str) and bool(value) and not any(c in value for c in "*?")


def hash_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


@dataclass
class Value:
    value: object
    support: list


class Evidence:
    def __init__(self, run):
        self.rows, self.support = {}, defaultdict(list)
        self.ignored_findings = 0
        self.associated_devices = defaultdict(set)
        self.device_scope_support = defaultdict(list)
        for finding in run.get("findings", []):
            if finding.get("status") != "verified":
                self.ignored_findings += 1
                continue
            fid = finding.get("finding_id")
            if not isinstance(fid, str) or not fid:
                raise ValueError("verified finding needs an ID")
            cited = {f["id"]: f for f in finding.get("cited_facts", [])}
            for part in finding.get("parts", []):
                name, args = next(iter(part["part"].items()))
                definition = claims.SETS.get(name)
                if definition is None or name == "tagged":
                    continue
                for param, fact_id in zip(definition.params, args):
                    if param != "fact":
                        continue
                    if fact_id not in cited:
                        raise ValueError(f"{fid} cites a missing fact {fact_id}")
                    fact = cited[fact_id]
                    if not re.fullmatch(r"[0-9a-f]{64}", fact.get("row_sha256", "")):
                        raise ValueError(f"{fid}: fact {fact_id} has no bound row hash")
                    if fact_id in self.rows and self.rows[fact_id] != fact:
                        raise ValueError(f"fact {fact_id} changes across certificates")
                    self.rows[fact_id] = fact
                    item = {"finding_id": fid, "fact_id": fact_id, "set": name,
                            "row_sha256": fact["row_sha256"], "strength": finding.get("strength")}
                    if item not in self.support[fact_id]:
                        self.support[fact_id].append(item)
                if name == "openedFromDevice" and len(args) == 2 and args[1] in cited:
                    exhibit = cited[args[1]].get("prov", {}).get("exhibit")
                    if exhibit:
                        self.associated_devices[args[0]].add(exhibit)
                        self.device_scope_support[args[0]].append({
                            "finding_id": fid, "fact_id": args[1], "set": name,
                            "row_sha256": cited[args[1]]["row_sha256"], "slot": "prov.exhibit",
                            "basis": "bound_provenance", "exhibit": exhibit,
                            "derivation": "checked target/device relation joined to the hashed physical exhibit label",
                            "relation_fact_ids": args, "direct_value": False})
        self.facts = sorted(self.rows.values(), key=lambda f: (f["t"], f["id"]))

    def of(self, kind):
        return [f for f in self.facts if f["kind"] == kind]

    def value(self, fact, slot, transform=None, derivation=None):
        raw = fact.get("prov", {}).get(slot[5:]) if slot.startswith("prov.") else fact.get(slot)
        if raw is None:
            return None
        converted = transform(raw) if transform else raw
        citations = []
        for support in self.support[fact["id"]]:
            item = dict(support, slot=slot,
                        basis="bound_provenance" if slot.startswith("prov.") else "certified_core")
            if derivation:
                item["derivation"] = derivation
                item["direct_value"] = False
            else:
                item["direct_value"] = True
            citations.append(item)
        return Value(converted, citations)

    def time(self, fact):
        return self.value(fact, "t", utc, "UTC microseconds converted to ISO 8601")

    def interpreted_time(self, fact, meaning_slot="prov.time_meaning"):
        value = self.time(fact)
        meaning = self.value(fact, meaning_slot)
        if meaning is not None:
            value.support.extend(meaning.support)
        return value


def _render(node, path=""):
    if isinstance(node, Value):
        return node.value, {path: node.support}
    if isinstance(node, dict):
        out, support = {}, {}
        for key, value in node.items():
            if value is None:
                continue
            rendered, cited = _render(value, path + "/" + str(key).replace("~", "~0").replace("/", "~1"))
            out[key] = rendered
            support.update(cited)
        return out, support
    if isinstance(node, list):
        out, support = [], {}
        for value in node:
            rendered, cited = _render(value, path + "/" + str(len(out)))
            out.append(rendered)
            support.update(cited)
        return out, support
    raise ValueError("every emitted answer leaf must have explicit support")


def _clean(record):
    return {k: v for k, v in record.items() if v is not None}


def _artifact_path(value):
    value = normalized_path(value)
    found = re.match(r"^(.*?\.(?:ost|pst|edb|snt|dat|db|pf))(?:\s|$)", value, re.I)
    return found.group(1) if found else None


def _browser_source_file(fact):
    """Prefer the reader's file field; recognize only known legacy locator forms.

    Chrome's history databases have no extension. The tail describes a database
    record, not part of the filename. An arbitrary locator is not a file path.
    """
    prov = fact.get("prov", {})
    if "source_file" in prov:
        value = prov["source_file"]
        slot = "prov.source_file"
    else:
        locator = prov.get("artifact", "")
        match = None
        if fact.get("aux_text", "").casefold() == "chrome":
            match = re.fullmatch(r"(.+) table (?:visits|urls|omni_box_shortcuts) id \d+", locator)
            if match is None:
                match = re.fullmatch(r"(.+) entry for history id \d+", locator)
        value = match[1] if match else _artifact_path(locator)
        slot = "prov.artifact"
    if not concrete_path(value):
        return None
    value = normalized_path(value)
    if not re.match(r"^[A-Za-z]:\\|^\\\\[^\\]+\\", value):
        return None
    return slot, value


def _program_contract_fields(evidence, fact):
    """Translate known artifact semantics into the public answer vocabulary.

    A source name alone cannot turn a file/key timestamp into execution. Unknown
    descriptions stay explicit; they are not silently assigned a familiar meaning.
    """
    slot, source = _source(fact)
    names = {"prefetch": "Prefetch", "userassist": "UserAssist",
             "application compatibility cache": "Shimcache", "shimcache": "Shimcache",
             "muicache": "MuiCache"}
    canonical = names.get(source.casefold(), source)
    original = fact.get("prov", {}).get("time_meaning", "")
    meaning = None
    if canonical == "Prefetch" and re.fullmatch(r"(?:last run time|earlier run time \d+) in the prefetch header", original):
        meaning = "execution"
    elif canonical == "UserAssist" and original == "last run time stored in the UserAssist entry":
        meaning = "execution"
    elif canonical == "Shimcache" and original == "last-modified time of the file as stored in the compatibility cache; not a run time":
        meaning = "file modification"
    no_time = ((canonical == "MuiCache" or source == "Program Compatibility Assistant")
               and original == "last-write time of the registry key; the list keeps no time per program")
    no_time = no_time or (source == "RecentFileCache.bcf" and original == "last-modified time of RecentFileCache.bcf; the cache keeps no time per program")
    no_time = no_time or (source == "open/save dialog history" and original == "last-write time of the registry key (set when the most recent entry, position 1, was written); the list keeps no time per program")
    if canonical == "Shimcache" and original == "last-write time of the AppCompatCache key; this entry stores no file time":
        no_time = True
    if no_time:
        meaning = "unreported"
    source_value = evidence.value(fact, slot, lambda _: canonical, "artifact source name in the public vocabulary")
    meaning_value = (evidence.value(fact, "prov.time_meaning", lambda _: meaning,
                                   "known artifact timestamp semantics in the public vocabulary")
                     if meaning else evidence.value(fact, "prov.time_meaning"))
    if meaning_value is not None and meaning:
        meaning_value.support.extend(source_value.support)
    timestamp = (evidence.value(fact, "prov.time_meaning", lambda _: None,
                                "artifact explicitly stores no per-program timestamp")
                 if no_time else evidence.time(fact))
    return source_value, meaning_value, timestamp


def _full_path(fact):
    p = fact.get("prov", {})
    if p.get("destlist_path"):
        return "prov.destlist_path", normalized_path(p["destlist_path"])
    path = normalized_path(fact["obj_text"])
    if re.match(r"^[A-Za-z]:\\|^\\\\", path):
        return "obj_text", path
    if p.get("original_drive") or p.get("drive_letter"):
        return ("prov.original_drive" if p.get("original_drive") else "prov.drive_letter",
                (p.get("original_drive") or p["drive_letter"]) + path)
    return "obj_text", path


def _source(fact):
    p = fact.get("prov", {})
    if p.get("source"):
        return "prov.source", p["source"]
    artifact = p.get("artifact", "").lower()
    if "automaticdestinations" in artifact or "customdestinations" in artifact:
        return "prov.artifact", "JumpList"
    if ".lnk" in artifact:
        return "prov.artifact", ".LNK"
    return "aux_text", fact["aux_text"]


def inventory_paths(evidence):
    """Concrete paths of fully hashed containers, classified by bound provenance.

    The certificate proves the fileContent row; directory-layout classification is
    hashed metadata, not a proof of container contents, usage, ownership or completeness.
    Unreadable fileSeen inventories and census-only claims are not used here.
    """
    paths = defaultdict(dict)
    categories = {"outlook_mailbox", "thumbnail_cache", "sticky_notes", "windows_search"}
    for fact in evidence.of("fileContent"):
        prov = fact.get("prov", {})
        category = prov.get("inventory_category")
        path = fact.get("obj_text")
        if (category not in categories or not concrete_path(path)
                or not re.match(r"^[A-Za-z]:\\|^\\\\[^\\]+\\", path)
                or prov.get("source_path") != path
                or prov.get("timestamp_semantics") != "examination_observation"
                or prov.get("hash_complete") is not True
                or prov.get("hash_algorithm") != "sha256"
                or not re.fullmatch(r"sha256:[0-9a-f]{64}", fact.get("aux_text", ""))
                or not any(s["set"] == "contentHashed" for s in evidence.support[fact["id"]])):
            continue
        value = evidence.value(fact, "obj_text", normalized_path, "concrete hashed container path")
        for slot in ("inventory_category", "source_path", "hash_complete", "hash_algorithm", "timestamp_semantics"):
            value.support.extend(evidence.value(fact, "prov." + slot).support)
        value.support.extend(evidence.value(fact, "aux_text").support)
        value.support = [support for support in value.support if support["set"] == "contentHashed"]
        key = value.value.casefold()
        if key in paths[category]:
            paths[category][key].support.extend(value.support)
        else:
            paths[category][key] = value
    return paths


def _merge_scalar_inventory(answer, qid, field, paths, other_paths=()):
    """A scalar contract cannot select one of multiple observed container paths."""
    if not paths:
        return
    candidates = dict(paths)
    previous = answer.get(qid, {}).get(field)
    for value in list(other_paths) + ([previous] if previous is not None else []):
        key = normalized_path(value.value).casefold()
        if key in candidates:
            for support in value.support:
                if support not in candidates[key].support:
                    candidates[key].support.append(support)
        else:
            candidates[key] = value
    if len(candidates) == 1:
        answer.setdefault(qid, {})[field] = next(iter(candidates.values()))
        return True
    else:
        # Preserve other independently supported fields; do not choose by profile
        # name, expected answer, first sighting, timestamp, or lexicographic order.
        answer.setdefault(qid, {}).pop(field, None)
        return False


def generate(run, profile):
    if profile.get("schema_version") != 2 or not profile.get("case_id"):
        raise ValueError("public questions need schema_version 2 and case_id")
    questions = profile.get("questions")
    if not isinstance(questions, list) or any("expected" in q for q in questions):
        raise ValueError("use a public questions profile with no expected answers")
    question_ids = [str(q["id"]) for q in questions]
    if len(set(question_ids)) != len(question_ids):
        raise ValueError("public question IDs must be unique")
    run_case = run.get("case_id", run.get("case", {}).get("case_id"))
    if run_case is not None and run_case != profile["case_id"]:
        raise ValueError("run case_id differs from the public question profile")
    zone = ZoneInfo(profile.get("time_zone", "UTC"))
    e = Evidence(run)
    answer = {}
    unresolved = {}
    settings = defaultdict(list)
    for f in e.of("systemSetting"):
        settings[f["obj_text"].casefold()].append(f)

    def setting(name, slot="aux_text", transform=None, derivation=None):
        rows = settings.get(name, [])
        if not rows:
            return None
        # Conflicting values are not resolved by looking at a reference answer.
        values = {str(f[slot]).casefold() for f in rows}
        if len(values) != 1:
            return None
        return e.value(rows[0], slot, transform, derivation)

    # Simple recorded system configuration.
    answer["Q3"] = _clean({"os_name": setting("operating system", transform=lambda s: re.sub(r" Service Pack \d+$", "", s),
                                             derivation="separate the appended CSDVersion service-pack label"),
                            "registered_owner": setting("registered owner"),
                            "system_root": setting("system root"),
                            "installed_at": setting("operating system installed", "t", utc, "UTC microseconds to ISO 8601")})
    versions = settings.get("operating system version", [])
    if versions and len({f["aux_text"] for f in versions}) == 1:
        f = versions[0]
        match = re.fullmatch(r"(\d+\.\d+)\.(\d+)", f["aux_text"])
        if match:
            answer["Q3"].update(version=e.value(f, "aux_text", lambda _: match[1], "CurrentVersion component of composite version"),
                                 build_number=e.value(f, "aux_text", lambda _: int(match[2]), "CurrentBuildNumber component of composite version"))
    answer["Q5"] = _clean({"computer_name": setting("computer name")})
    answer["Q8"] = _clean({"last_shutdown": setting("last shutdown", "t", utc, "ShutdownTime converted to ISO 8601")})
    if settings.get("time zone"):
        f = settings["time zone"][0]
        answer["Q4"] = _clean({"time_zone": e.value(f, "aux_text"),
            "standard_utc_offset_hours": e.value(f, "prov.bias_minutes", lambda x: -x / 60, "Windows Bias minutes negated and divided by 60"),
            "daylight_time_bias_hours": e.value(f, "prov.daylight_bias_minutes", lambda x: -x / 60, "Windows DaylightBias minutes negated and divided by 60")})
    interfaces = []
    for f in settings.get("network address", []):
        fields = {"device_name": "adapter_description", "subnet_mask": "subnet_mask", "name_server": "name_server",
                  "domain": "dns_domain", "default_gateway": "default_gateway", "dhcp_enabled": "dhcp_enabled", "dhcp_server": "dhcp_server"}
        interfaces.append(_clean({"ip_address": e.value(f, "aux_text"), **{k: e.value(f, "prov." + v) for k, v in fields.items()}}))
    if interfaces:
        answer["Q9"] = {"interfaces": interfaces}
    images = defaultdict(dict)
    for name, field in (("image md5", "md5"), ("image sha1", "sha1")):
        for f in settings.get(name, []):
            image = f.get("prov", {}).get("exhibit")
            if image:
                images[image].update(image=e.value(f, "prov.exhibit"), **{field: e.value(f, "aux_text")})
    if images:
        answer["Q1"] = {"images": list(images.values())}
    partitions = []
    for f in settings.get("disk partition", []):
        m = re.fullmatch(r"partition (\d+): (.*), start sector (\d+), sectors (\d+)", f["aux_text"])
        if m:
            fields = {"number": (1, int), "filesystem": (2, str), "start_sector": (3, int), "total_sectors": (4, int)}
            part = {key: e.value(f, "aux_text", lambda _, g=g, cast=cast, m=m: cast(m[g]), "parse the recorded partition-table summary")
                    for key, (g, cast) in fields.items()}
            part["bootable"] = e.value(f, "prov.bootable")
            partitions.append(_clean(part))
    if partitions:
        answer["Q2"] = {"partitions": partitions}

    accounts, installed, executions, sessions, visits, searches, typed = [], [], [], [], [], [], []
    os_start = min((f["t"] for f in settings.get("operating system installed", [])), default=None)
    for f in e.of("accountSeen"):
        if f["aux_text"] == "windows local account" and f["obj_text"].casefold() not in {"administrator", "guest", "systemprofile", "localservice", "networkservice"}:
            accounts.append(_clean({"account": e.value(f, "obj_text"), "rid_as_printed": e.value(f, "prov.rid"),
                                    "login_count": e.value(f, "prov.logon_count")}))
    if accounts:
        answer["Q6"] = {"accounts": accounts}
    for f in e.of("programInstalled"):
        if os_start is not None and f["t"] < os_start:
            continue
        installed.append(_clean({"name": e.value(f, "obj_text"),
            "version": e.value(f, "aux_text") if f["aux_text"] not in ("", "(none)") else None,
            "manufacturer": e.value(f, "prov.publisher"), "installation_path": e.value(f, "prov.install_location")}))
    if installed:
        answer["Q10"] = {"applications": installed}
    for f in e.of("programRun"):
        source, meaning, timestamp = _program_contract_fields(e, f)
        executions.append(_clean({"timestamp": timestamp, "path_or_application_id": e.value(f, "aux_text") if f["aux_text"] not in ("", "(none)") else e.value(f, "obj_text"),
            "execution_count": e.value(f, "prov.run_count"), "source": source,
            "time_meaning": meaning}))
    if executions:
        answer["Q11"] = {"records": executions}
    q12 = next((q for q in questions if str(q["id"]) == "Q12"), {})
    hour_bounds = re.findall(r"\b(\d\d:\d\d)\b", q12.get("prompt", ""))[:2]
    for f in e.of("sessionEvent"):
        p = f.get("prov", {})
        clock = datetime.fromisoformat(utc(f["t"]).replace("Z", "+00:00")).astimezone(zone).strftime("%H:%M")
        if p.get("source") != "event log" or (os_start is not None and f["t"] < os_start):
            continue
        if len(hour_bounds) == 2 and not hour_bounds[0] <= clock <= hour_bounds[1]:
            continue
        sessions.append(_clean({"timestamp": e.time(f), "event_id": e.value(f, "prov.event_id"), "description": e.value(f, "obj_text")}))
    if sessions:
        answer["Q12"] = {"events": sessions}
    for f in e.of("webVisit"):
        visits.append({"timestamp": e.time(f), "url": e.value(f, "obj_text"), "browser": e.value(f, "aux_text")})
    if visits:
        answer["Q15"] = {"visits": visits}
        browsers = {}
        for f in e.of("webVisit"):
            browsers.setdefault(f["aux_text"], {"name": e.value(f, "aux_text")})
        answer["Q13"] = {"browsers": list(browsers.values())}
    browser_artifacts = {}
    for f in e.of("webVisit"):
        p = f.get("prov", {})
        candidates = []
        if concrete_path(p.get("container_folder")):
            candidates.append(("prov.container_folder", normalized_path(p["container_folder"])))
        source_file = _browser_source_file(f)
        if source_file is not None:
            candidates.append(source_file)
        for slot, path in candidates:
            if re.match(r"^[A-Za-z]:\\|^\\\\[^\\]+\\", path):
                browser_artifacts.setdefault((f["aux_text"], path.casefold()), {
                    "browser": e.value(f, "aux_text"),
                    "path": e.value(f, slot, lambda _, path=path: path, "history artifact path from the recorded locator")})
    if browser_artifacts:
        answer["Q14"] = {"artifacts": list(browser_artifacts.values())}
    for f in e.of("webSearch"):
        searches.append(_clean({"timestamp": e.time(f), "keyword": e.value(f, "obj_text"), "browser": e.value(f, "aux_text"), "url": e.value(f, "prov.url")}))
    if searches:
        answer["Q16"] = {"searches": searches}
    for f in e.of("localSearch"):
        typed.append({"timestamp": e.time(f), "keyword": e.value(f, "obj_text")})
    if typed:
        answer["Q17"] = {"searches": typed}

    mail_accounts = [f for f in e.of("accountSeen") if "e-mail" in f["aux_text"] or "email" in f["aux_text"]]
    if mail_accounts and len({f["obj_text"].casefold() for f in mail_accounts}) == 1:
        answer["Q20"] = {"account": e.value(mail_accounts[0], "obj_text")}
    mailbox = next((f for f in mail_accounts if _artifact_path(f.get("prov", {}).get("artifact", ""))), None)
    mailbox_paths = [e.value(f, "prov.artifact", _artifact_path, "mailbox file path from artifact locator")
                     for f in mail_accounts if _artifact_path(f.get("prov", {}).get("artifact", ""))]
    if mailbox:
        answer["Q19"] = {"path_as_printed": e.value(mailbox, "prov.artifact", _artifact_path, "mailbox file path from artifact locator")}
    messages = []
    for f in e.of("emailSent"):
        sender = f.get("prov", {}).get("sender_address")
        sender_status = f.get("prov", {}).get("sender_address_status")
        # Legacy readers used an empty string for an unavailable MAPI property.
        # Neither an absent property nor an empty address supplies a sender.
        sender_known = isinstance(sender, str) and bool(sender.strip()) and sender_status not in ("missing", "unavailable", "empty")
        message = _clean({"timestamp": e.time(f), "subject": e.value(f, "obj_text"),
                          "folder_or_recovery_source": e.value(f, "prov.folder"),
                          "from": e.value(f, "prov.sender_address") if sender_known else None})
        if sender_known and sender_status is not None:
            message["from"].support.extend(e.value(f, "prov.sender_address_status").support)
        if f.get("prov", {}).get("attachments") == 0:
            message["attachments"] = e.value(f, "prov.attachments", lambda _: [], "recorded zero attachment count")
        messages.append(message)
    if messages:
        answer["Q21"] = {"messages": messages}

    devices = defaultdict(dict)
    for f in e.of("usbInsert"):
        dev = devices[f["obj_text"]]
        dev["serial_number"] = e.value(f, "obj_text")
        meaning = f.get("prov", {}).get("time_meaning", "").lower()
        if "first connection" in meaning:
            dev["first_connected"] = e.time(f)
        elif "reboot" in meaning:
            dev["connected_after_reboot"] = e.time(f)
        descriptor = f.get("prov", {}).get("device", "")
        m = re.search(r"Ven_([^&]+)&Prod_([^&]+)", descriptor)
        if m:
            dev["device_name"] = e.value(f, "prov.device", lambda _, m=m: (m[1] + " " + m[2]).replace("_", " ") + " USB Device", "decode USBSTOR vendor/product descriptor")
    if devices:
        answer["Q22"] = {"devices": list(devices.values())}
    renames = []
    q23 = next((q for q in questions if str(q["id"]) == "Q23"), {})
    dates = re.findall(r"\b\d{4}-\d\d-\d\d\b", q23.get("prompt", ""))[:2]
    for f in e.of("fileRenamed"):
        when = datetime.fromisoformat(utc(f["t"]).replace("Z", "+00:00")).astimezone(zone).date().isoformat()
        if len(dates) == 2 and not dates[0] <= when <= dates[1]:
            continue
        if "\\desktop\\" not in f["obj_text"].casefold() and "\\desktop\\" not in f["aux_text"].casefold():
            continue
        record = {"timestamp": e.time(f), "old_name": e.value(f, "obj_text", lambda s: PureWindowsPath(s).name, "basename of recorded old path"),
                  "new_name": e.value(f, "aux_text", lambda s: PureWindowsPath(s).name, "basename of recorded new path"),
                  "old_usn": e.value(f, "prov.old_name_usn")}
        usn = re.search(r"\bUSN (\d+)\b", f.get("prov", {}).get("artifact", ""))
        if usn:
            record["new_usn"] = e.value(f, "prov.artifact", lambda _, n=int(usn[1]): n, "USN parsed from artifact locator")
        renames.append(_clean(record))
    if renames:
        answer["Q23"] = {"renames": renames}

    network_hosts, network_folders, network_opens, device_opens = {}, [], [], defaultdict(list)
    for f in e.facts:
        if f["kind"] not in ("lnkTarget", "folderOpened", "fileSeen"):
            continue
        slot, path = _full_path(f)
        path_value = e.value(f, slot, lambda _, p=path: p, "recorded path; join recorded drive prefix only if needed")
        if slot.startswith("prov.") and slot != "prov.destlist_path":
            path_value.support.extend(e.value(f, "obj_text").support)
        src_slot, source = _source(f)
        record = {"timestamp": e.time(f), "path": path_value,
                  "source": e.value(f, src_slot, lambda _, s=source: s, "artifact source classification")}
        if path.startswith("\\\\"):
            host = path[2:].split("\\")[0]
            try:
                ipaddress.ip_address(host)
                network_hosts[host] = e.value(f, slot, lambda _, h=host: h, "IP host from recorded UNC path")
            except ValueError:
                pass
            if f["kind"] == "folderOpened":
                network_folders.append(record)
            elif f["kind"] == "lnkTarget" or f["aux_text"] == "office recent files":
                network_opens.append(record)
        if f["kind"] == "lnkTarget":
            for exhibit in e.associated_devices[f["id"]]:
                scope = [s for s in e.device_scope_support[f["id"]] if s["exhibit"] == exhibit]
                device_opens[exhibit].append({key: Value(value.value, value.support + scope)
                                              for key, value in record.items()})
    if len(network_hosts) == 1:
        answer["Q24"] = {"ip_address": next(iter(network_hosts.values()))}
    if network_folders:
        answer["Q27"] = {"records": network_folders}
    if network_opens:
        answer["Q28"] = {"records": network_opens}
    for exhibit, qid in (("RM#2", "Q26"), ("RM#3", "Q35")):
        if device_opens[exhibit]:
            answer[qid] = {"records": device_opens[exhibit]}
    cloud_accounts = [f for f in e.of("accountSeen") if "google drive" in f["aux_text"].lower()
                      and "credentials" in f.get("prov", {}).get("time_meaning", "")]
    if cloud_accounts and len({f["obj_text"] for f in cloud_accounts}) == 1:
        first = min(cloud_accounts, key=lambda f: f["t"])
        answer["Q31"] = {"account": e.value(first, "obj_text"), "logon_time": e.interpreted_time(first)}

    notes, caches, desktop_index, copies, recycling = [], {}, [], [], []
    note_paths, search_paths = [], []
    for f in e.of("noteText"):
        # A compound-storage stream timestamp is not the containing file's time.
        if "last-modified time of the" in f.get("prov", {}).get("time_meaning", "") and "file" in f["prov"]["time_meaning"]:
            notes.append({"file_modified": e.interpreted_time(f), "content": e.value(f, "obj_text")})
        path = _artifact_path(f.get("prov", {}).get("artifact", ""))
        if path:
            value = e.value(f, "prov.artifact", _artifact_path, "note storage file from artifact locator")
            note_paths.append(value)
            answer.setdefault("Q40", {"path": value})
    if notes:
        answer["Q41"] = {"notes": notes}
    for f in e.of("fileSeen"):
        if "inventory_category" in f.get("prov", {}):
            continue  # Inventory answer export requires a complete contentHashed claim.
        artifact = f.get("prov", {}).get("artifact", "")
        cache = re.search(r"([A-Za-z]:\\.*?thumbcache_[^\\ ]+\.db)\b", artifact, re.I)
        if cache and concrete_path(cache[1]):
            caches.setdefault(normalized_path(cache[1]).casefold(), e.value(f, "prov.artifact", lambda _, p=cache[1]: normalized_path(p), "thumbnail database path from artifact locator"))
        if f["aux_text"] == "windows search index":
            database = _artifact_path(artifact)
            if database:
                value = e.value(f, "prov.artifact", _artifact_path, "search database from artifact locator")
                search_paths.append(value)
                answer.setdefault("Q42", {"database_path": value})
            if "\\desktop\\" in f["obj_text"].casefold() and f.get("prov", {}).get("column") == "System_DateCreated":
                desktop_index.append({"date_created": e.interpreted_time(f, "prov.column"), "path": e.value(f, "obj_text", normalized_path, "canonical path separators")})
    if caches:
        answer["Q38"] = {"paths": list(caches.values())}
    if desktop_index:
        answer["Q46"] = {"records": desktop_index}
    for f in e.of("shadowCopy"):
        copies.append(_clean({"storage_path": e.value(f, "prov.artifact"), "created_at": e.time(f),
                              "shadow_copy_id": e.value(f, "obj_text"), "shadow_copy_set_id": e.value(f, "prov.shadow_copy_set_id"),
                              "size_bytes": e.value(f, "prov.size")}))
    if copies:
        answer["Q47"] = {"copies": copies}
    for f in e.of("fileDeleted"):
        found = re.search(r"Recycle Bin index (\$I[^, ]+)", f.get("prov", {}).get("artifact", ""))
        if found:
            slot, path = _full_path(f)
            value = e.value(f, slot, lambda _, p=path: p, "original path with recorded drive prefix")
            if slot.startswith("prov."):
                value.support.extend(e.value(f, "obj_text").support)
            recycling.append({"i_filename": e.value(f, "prov.artifact", lambda _, n=found[1]: n, "Recycle Bin index filename from artifact locator"),
                              "deleted_at": e.time(f), "original_path": value})
    if recycling:
        answer["Q51"] = {"records": recycling}

    inventory = inventory_paths(e)
    for qid, field, category, other_paths in (
            ("Q19", "path_as_printed", "outlook_mailbox", mailbox_paths),
            ("Q40", "path", "sticky_notes", note_paths),
            ("Q42", "database_path", "windows_search", search_paths)):
        if _merge_scalar_inventory(answer, qid, field, inventory[category], other_paths) is False:
            unresolved[qid] = ("Multiple supported container paths conflict with the scalar public answer field; "
                               "no path selected without independently supported scope.")
    if inventory["thumbnail_cache"]:
        for key, value in inventory["thumbnail_cache"].items():
            if key in caches:
                value.support.extend(caches[key].support)
            caches[key] = value
        answer["Q38"] = {"paths": [caches[key] for key in sorted(caches)]}

    responses = []
    for qid in question_ids:
        value = answer.get(qid)
        if not value:
            responses.append({"question_id": qid, "status": "unknown", "reason": unresolved.get(qid,
                              "No supported mapping from the supplied certified statements; no negative or intent inferred.")})
            continue
        rendered, support = _render(value)
        responses.append({"question_id": qid, "status": "answered", "answer": rendered,
                          "support": support, "full_answer_lean_certified": False})
    support_counts = Counter(c["basis"] for a in responses for refs in a.get("support", {}).values() for c in refs)
    return {"schema_version": 2, "case_id": profile["case_id"], "adapter_version": VERSION,
            "answers": responses, "run_sha256": hash_json(run), "public_questions_sha256": hash_json(profile),
            "adapter_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "source_findings": len(run.get("findings", [])), "eligible_facts": len(e.facts),
            "nonverified_findings_ignored": e.ignored_findings, "support_counts": dict(support_counts),
            "trust_boundary": "Input is a trusted checker-produced run whose certificates, fact hashes and string bindings must be independently reverified. This adapter does not replay Lean.",
            "certification_note": "certified_core denotes a cited encoded fact field. bound_provenance denotes metadata bound by the certificate row hash, not a Lean-proved semantic claim. Derivations are explicit. No whole answer or list completeness is claimed Lean-certified.",
            "selection": "Uses only the supplied run and public question profile; no reference values, scores, or answer key. Source-specific record multiplicity is preserved. Entity inventories (browser names, artifact paths) are distinct by recorded identity; no key-directed pruning of extra records."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--questions", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    output = Path(args.out)
    if output.exists():
        parser.error("output already exists; refusing to overwrite")
    try:
        result = generate(json.loads(Path(args.run).read_text()), json.loads(Path(args.questions).read_text()))
    except (ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    result["inputs"] = {name: {"path": str(path), "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}
                        for name, path in (("run", args.run), ("public_questions", args.questions))}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as stream:
        stream.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    counts = Counter(a["status"] for a in result["answers"])
    print(f"{counts['answered']} questions with supported fields; {counts['unknown']} unknown. Whole answers are not claimed Lean-certified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
