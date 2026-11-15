"""Restricted evidence access, checked claims, and persistent investigation work:

  sql / fact   look at the extracted records (read-only)
  forms        see which kinds of statement it may propose
  check        propose a statement; the Lean kernel accepts or refuses it

The investigator never writes a finding. It names records by id and picks a statement
form; the sentence shown to a person is generated from the records after the kernel
accepts. Every proposal, accepted or refused, is logged in the run directory.
"""
from __future__ import annotations

import json
import re
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

from checker import check as checker
from checker import claims, needs
from checker.facts import Fact, open_source
from agent.audit import AuditLog, audited

ROW_LIMIT = 60
CELL_LIMIT = 240
STEP_LIMIT = 20_000_000     # stop runaway queries

# One line per statement form: its arguments, and what the generated sentence says.
FORMS = {
    "usbConnected":       ("[usbInsert]", "USB device S was connected to this PC (time)."),
    "deviceHolds":        ("[usbInsert, volumeOnDevice]", "USB device S was connected (time); the seized device with that serial holds volume V. Needs the same device serial in both."),
    "opened":             ("[lnkTarget]", "Path P on volume/share X was opened (time)."),
    "openedFromDevice":   ("[lnkTarget, volumeOnDevice]", "P was opened (time) from volume V, the volume on seized device S. Needs the same volume serial in both."),
    "openedFromRecorded": ("[lnkTarget, volumeSeen]", "P was opened (time) from volume V, which this PC recorded under label L. Needs the same volume serial."),
    "recordedOnDevice":   ("[volumeSeen, volumeOnDevice]", "Volume V, recorded by this PC under label L, is the volume on seized device S. Needs the same volume serial."),
    "sameLabel":          ("[volumeSeen, volumeSeen]", "Two volumes were recorded under the same label. This does not identify one physical device. Needs the same label, two different records."),
    "searched":           ("[webSearch]", 'A web search for "Q" was made in browser B (time).'),
    "fileCreatedAt":      ("[fileCreated]", "P was created on volume V (time)."),
    "fileModifiedAt":     ("[fileModified]", "P was last modified on volume V (time)."),
    "fileDeletedAt":      ("[fileDeleted]", "P on volume V was sent to the Recycle Bin (time)."),
    "fileRemovedAt":      ("[fileRemoved]", "The NTFS journal carries a removal flag for P on volume V (record time). Flags can accumulate until close: this is not necessarily deletion onset, Recycle Bin use or wiping."),
    "fileCreationRecordedAt": ("[fileCreationRecorded]", "The NTFS journal carries a creation flag for P on volume V (record time). It is not a filesystem creation timestamp and cannot support copiedHere."),
    "volumeRecordedAt":   ("[volumeRecorded]", "The UDF file-set descriptor on physical disc D, volume V, records this timestamp. It is not examination time or proof that formatting/writing completed."),
    "createdAfterVolumeRecord": ("[fileCreated, volumeRecorded]", "Filesystem creation timestamp follows the UDF file-set recording timestamp on the same volume and identified disc. Needs matching volume serial and strict order beyond uncertainty; does not prove a completed burn or copy."),
    "journalNamed": ("[journalName]", "The journal records a name/path for an image-scoped NTFS volume/file-record/sequence identity at this observation time; not creation onset."),
    "journalParentRecorded": ("[journalParent]", "The journal records a child identity and parent-directory identity at the observation time."),
    "journalRemovalObserved": ("[journalRemoval]", "The journal carries a removal flag under a name/path for a scoped NTFS identity; not exact deletion onset, removal of all aliases, or secure wiping."),
    "sameJournalFile": ("[journalName, journalName]", "Two names at their own observation times share the same scoped NTFS identity. Different record/sequence/volume/image identities cannot join. Not unchanged content."),
    "removedFilePreviouslyNamed": ("[journalName, journalRemoval]", "An earlier journal name and later removal-flag observation share the same scoped identity. Needs strict time separation; does not backdate removal to the earlier alias or prove wiping."),
    "journalChildNamedDirectory": ("[journalName, journalParent, journalName]", "A child name, its parent reference, and the directory's name join through exact scoped identities. Each keeps its own timestamp; it does not imply presence under a later directory alias."),
    "journalPathAt": ("[journalPath]", "A path or explicitly incomplete suffix at the child journal observation time, reconstructed using intact USN-v2 byte intervals and directory identity/name transitions. Not filesystem creation, copying, or a disc write."),
    "journalPathForFile": ("[journalName, journalPath]", "The direct journal name and bounded path observation share the same scoped NTFS file identity. Each retains its own timestamp."),
    "emailed":            ("[emailSent]", 'An e-mail with the subject "S" was sent from A to B (time).'),
    "burnTrace":          ("[cdBurn]", "HEURISTIC. Optical-disc activity record (time). A lock or settings change does not establish a write, completion, contents, or physical-disc identity."),
    "deviceExamined":     ("[usbInsert, unallocatedOnDevice]", "USB device S was connected (time); the seized device with that serial has directory entries left in unallocated space. Needs the same device serial."),
    "recoveredOnDevice":  ("[fileCreated, unallocatedOnDevice]", "A directory entry for P, created (time), was recovered from device S. It may be an earlier state of the same file system; it does not establish a reformat. Needs the same area id in both aux fields."),
    "settingRecorded":    ("[systemSetting]", 'The system setting "N" is recorded as "V" (record time).'),
    "accountRecorded":    ("[accountSeen]", "An account named A is recorded (what it is an account of; record time)."),
    "sessionRecorded":    ("[sessionEvent]", "A logon / logoff / startup / shutdown is recorded for account A or the machine (time)."),
    "programInstalledAt": ("[programInstalled]", "Program N version V is recorded as installed (time)."),
    "programRan":         ("[programRun]", "An application artifact names E and its recorded timestamp meaning. Only explicit prefetch/UserAssist/process-creation run-time records say execution time; cache/key/file timestamps do not."),
    "visited":            ("[webVisit]", "Browser B's history records a visit to URL U (time)."),
    "downloaded":         ("[fileDownloaded]", "A download from URL U to path P is recorded (time)."),
    "typedInSearchBox":   ("[localSearch]", 'The text "T" is recorded as typed into a search box of the operating system (record time).'),
    "cloudEvent":         ("[cloudFile]", 'A cloud-client record reads "<service>: <event>" for file F (time).'),
    "noteFound":          ("[noteText]", 'A note of application A reads "T" (last modified time).'),
    "folderRecorded":     ("[folderOpened]", "A shell-bag or similar record names folder P (record time)."),
    "renamed":            ("[fileRenamed]", "Old name was renamed to new name (time)."),
    "fileRecorded":       ("[fileSeen]", "A secondary artifact (search index, thumbnail cache, shadow copy, ...) holds a record of path P (record time)."),
    "shadowCopyMade":     ("[shadowCopy]", "Shadow copy I of volume V was created (time)."),
    "contentHashed":      ("[fileContent]", "The content of path P, read from the image, has SHA-256 H."),
    "sameContent":        ("[fileContent, fileContent]", "Two paths have identical content. Needs the same hash in both records, two different records."),
    "exactly":            ('[kind name, n]', "CENSUS. The evidence holds exactly n records of that kind (n may be 0). About the records extracted, not about what happened. Stands alone: not inside `both`."),
    "exactlyDistinct":    ('[kind name, "obj" or "aux", n]', "CENSUS. The records of that kind name exactly n different values in that field (for example: usbInsert, obj, 2 = two different device serials)."),
    "exactlyWith":        ('[kind name, "obj" or "aux", entity id, n]', "CENSUS. Exactly n records of that kind have that entity in that field (n = 0: none has). Take the entity id from `fact <id>` (obj_id / aux_id)."),
    "copiedHere":         ("[fileCreated, fileModified]", "HEURISTIC. P was likely copied onto volume V: created there after its last modification. Needs the same path and volume, and modified before created."),
    "deletedAfter":       ("[fileDeleted, any record]", "P was deleted (time) after the other event."),
    "before":             ("[any record, any record]", "The first event happened before the second, by more than both timestamps' uncertainty."),
    "tagged":             ('[record, "obj" or "aux", tag record, tag record\'s aux_id]', "The entity in that slot of the record carries this tag. Take aux_id from `fact <tag id>`."),
    "usbMountedAs":       ("[usbInsert, volumeMount]", "USB device S was connected and mounted as volume V."),
    "openedFromMount":    ("[lnkTarget, volumeMount]", "P was opened from the volume a mount record names."),
}


def _utc(t: int) -> str:
    dt = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=t)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _read_only(action, *_):
    allowed = (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION,
               sqlite3.SQLITE_RECURSIVE)
    return sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY


class Workbench:
    def __init__(self, facts_path, run_dir, proposer: str = "agent"):
        # API tools can run in worker threads. Share one evidence store, while
        # serializing its cursors, query budget, and run-log ID allocation.
        self._lock = threading.RLock()
        self.source = open_source(facts_path)
        self.run_dir = Path(run_dir)
        self.proposer = proposer
        self._db = self._load()
        self._audit = AuditLog(self.run_dir / "audit.jsonl", self._lock)
        metadata = getattr(self.source, "metadata", None)
        if metadata is not None:
            encoded = json.dumps(metadata, sort_keys=True, indent=2) + "\n"
            try:
                with (self.run_dir / "extraction-metadata.json").open("x") as stream:
                    stream.write(encoded)
            except FileExistsError:
                pass

    # ---- looking at records -------------------------------------------------------

    def _load(self) -> sqlite3.Connection:
        db = sqlite3.connect(":memory:", check_same_thread=False)
        db.execute("CREATE TABLE facts (id INTEGER PRIMARY KEY, kind TEXT, time_utc TEXT, "
                   "t_us INTEGER, uncertainty_us INTEGER, obj TEXT, aux TEXT, exhibit TEXT, "
                   "artifact TEXT, detail TEXT)")
        for f in self.source.all():
            prov = {k: v for k, v in f.prov.items() if k not in ("image", "tool")}
            exhibit, artifact = prov.pop("exhibit", ""), prov.pop("artifact", "")
            db.execute("INSERT INTO facts VALUES (?,?,?,?,?,?,?,?,?,?)",
                       (f.id, f.kind, _utc(f.t), f.t, f.res, self.source.string(f.obj),
                        self.source.string(f.aux), exhibit, artifact,
                        json.dumps(prov, sort_keys=True, ensure_ascii=False)))
        db.commit()
        db.set_authorizer(_read_only)
        steps = {"n": 0}

        def tick():
            steps["n"] += 1
            return 1 if steps["n"] * 10_000 > STEP_LIMIT else 0
        db.set_progress_handler(tick, 10_000)
        self._steps = steps
        return db

    @audited
    def sql(self, query: str) -> dict:
        """Run one read-only SELECT over the `facts` table."""
        with self._lock:
            self._steps["n"] = 0
            cur = None
            try:
                cur = self._db.execute(query)
                cols = [c[0] for c in cur.description or []]
                rows = cur.fetchmany(ROW_LIMIT + 1)
            except (sqlite3.Error, sqlite3.Warning) as e:   # Warning: more than one statement
                return {"error": str(e), "hint": "one SELECT over table facts(id, kind, time_utc, "
                        "t_us, uncertainty_us, obj, aux, exhibit, artifact, detail)"}
            finally:
                if cur is not None:
                    cur.close()
        clip = lambda v: v[:CELL_LIMIT] + "…" if isinstance(v, str) and len(v) > CELL_LIMIT else v
        out = {"columns": cols, "rows": [[clip(v) for v in r] for r in rows[:ROW_LIMIT]]}
        if len(rows) > ROW_LIMIT:
            out["truncated"] = f"more than {ROW_LIMIT} rows; narrow the query"
        return out

    @audited
    def fact(self, fact_id: int) -> dict:
        with self._lock:
            found = self.source.get([fact_id])
            if fact_id not in found:
                return {"error": f"no record with id {fact_id}"}
            f = found[fact_id]
            return {"id": f.id, "kind": f.kind, "time_utc": _utc(f.t), "t_us": f.t,
                    "uncertainty_us": f.res, "obj": self.source.string(f.obj), "obj_id": f.obj,
                    "aux": self.source.string(f.aux), "aux_id": f.aux, "provenance": f.prov}

    @audited
    def forms(self) -> dict:
        return {"how": 'A claim is {"form": [record ids...]}. Join several with '
                       '{"both": [claim, claim, ...]}: every part must hold.',
                "forms": {name: {"arguments": args, "says": says,
                                 "strength": claims.SETS[name].strength}
                          for name, (args, says) in FORMS.items()}}

    # ---- investigation workflow ---------------------------------------------------

    @audited
    def plan(self) -> dict:
        """Current question work, with agent-reported status separate from proof."""
        from agent.investigation import Investigation
        state = Investigation(self.run_dir).snapshot()
        # Full history stays on disk and in the report; the agent needs current work.
        return {key: value for key, value in state.items() if key != "history"}

    @audited
    def update_question(self, question_id: str, finding_ids=None, searched=None,
                        unresolved=None, next_actions=None, status=None) -> dict:
        """Save question progress and references to this run's checked findings."""
        from agent.investigation import Investigation
        return Investigation(self.run_dir).update(question_id, finding_ids=finding_ids,
            searched=searched, unresolved=unresolved, next_actions=next_actions, status=status)

    @audited
    def evidence_needs(self, proof_gap=None) -> dict:
        """Available approved readers and diagnostic follow-up suggestions."""
        from agent.evidence_requests import recommendations
        return recommendations(self.run_dir, proof_gap=proof_gap)

    @audited
    def collect(self, reader: str, exhibit: str) -> dict:
        """Run an approved reader on configured evidence into a new snapshot."""
        from agent.evidence_requests import collect
        return collect(self.run_dir, reader, exhibit)

    @audited
    def review(self) -> dict:
        """Conservative cross-record diagnostics, not certified findings."""
        from agent.review import review
        result = review(self.source)
        path = self.run_dir / "review.json"
        if path.is_symlink():
            raise ValueError("Review output must not be a symlink")
        from agent.investigation import atomic_json
        atomic_json(path, result)
        return result

    # ---- proposing ----------------------------------------------------------------

    def _log(self) -> List[dict]:
        with self._lock:
            path = self.run_dir / "proposals.jsonl"
            if not path.is_file():
                return []
            return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

    @audited
    def check(self, question: str, claim, revises=None) -> dict:
        """Propose a claim. Returns the kernel's verdict, with the reason if refused."""
        if isinstance(claim, str):
            try:
                claim = json.loads(claim)
            except json.JSONDecodeError as e:
                reason = f"claim is not valid JSON: {e}"
                return {"status": "rejected", "reason": reason,
                        "proof_gap": needs.malformed(reason)}
        with self._lock:
            log = self._log()
            if revises is not None:
                from agent.history import validate_revision
                try:
                    validate_revision(revises, log, current_id=f"A{len(log) + 1:03d}")
                except ValueError as error:
                    return {"status": "rejected", "reason": str(error),
                            "proof_gap": needs.malformed(str(error))}
            key = json.dumps(claim, sort_keys=True)
            for earlier in log:
                if json.dumps(earlier.get("claim"), sort_keys=True) == key:
                    if revises is None:
                        return dict(self._brief(earlier), note=f"already proposed as {earlier['finding_id']}")
                    if earlier["finding_id"] == revises:
                        reason = "An explicit revision must change the earlier claim; this proposal is unchanged."
                        return {"status": "rejected", "reason": reason,
                                "proof_gap": needs.malformed(reason)}
            result = checker.check(claim, f"A{len(log) + 1:03d}", self.source, question,
                                   self.run_dir, proposer=self.proposer)
            if result.get("status") == "verified" and (self.run_dir / "investigation.json").is_file():
                from agent.investigation import Investigation
                planner = Investigation(self.run_dir)
                matched = [q for q in planner.snapshot()["questions"] if question in (q["id"], q["prompt"])]
                if len(matched) == 1:
                    planner.update(matched[0]["id"], finding_ids=[result["finding_id"]], status="in_progress")
            return self._brief(result)

    @audited
    def conclude(self, text: str, finding_ids) -> dict:
        """Record a conclusion (judgment). It must rest on certified findings of this run."""
        from agent.conclusions import Conclusions
        with self._lock:
            return Conclusions(self.run_dir).add(text, finding_ids, self._log(), self.proposer)

    def _brief(self, r: dict) -> dict:
        if r["status"] == "verified":
            return {"status": "verified", "finding_id": r["finding_id"], "strength": r["strength"],
                    "rules": r["rules"], "sentence": r["english"]}
        out = {"status": "rejected", "finding_id": r["finding_id"], "reason": r.get("reason", "")}
        if "proof_gap" in r:
            out["proof_gap"] = r["proof_gap"]
        failing = [b for p in r.get("parts", []) for b in p["bricks"] if b.startswith("FAIL")]
        if failing:
            out["failing_checks"] = [self._why(b) for b in failing]
        return out

    def _why(self, brick: str) -> str:
        """Spell out a failing check with the values involved (for feedback only)."""
        ids = [int(n) for n in re.findall(r"\b\d+\b", brick)]
        slots = re.findall(r"\b(obj|aux)\b", brick)
        got: Dict[int, Fact] = self.source.get(ids)
        name = brick.split()[1] if len(brick.split()) > 1 else ""
        s = self.source.string
        try:
            if name == "link" and len(ids) >= 2 and len(slots) >= 2:
                a, b = got[ids[0]], got[ids[1]]
                return (f"{brick}: record {a.id} {slots[0]} is {s(getattr(a, slots[0]))!r} but "
                        f"record {b.id} {slots[1]} is {s(getattr(b, slots[1]))!r}")
            if name == "before" and len(ids) >= 2:
                a, b = got[ids[0]], got[ids[1]]
                return (f"{brick}: record {a.id} is at {_utc(a.t)} and record {b.id} at "
                        f"{_utc(b.t)}; the first is not earlier by more than the uncertainty")
            if name == "is" and ids:
                return f"{brick}: record {ids[0]} is of kind {got[ids[0]].kind}"
        except (KeyError, IndexError):
            pass
        return brick

    @audited
    def answer(self, question_id: str, bindings=None, replace=False) -> dict:
        """Save explicit claim-field bindings, or show the supported field catalog."""
        from agent.answer_store import answer
        return answer(self.run_dir, question_id, bindings, replace=replace)
