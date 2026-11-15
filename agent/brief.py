"""Shared record/tool instructions rendered with public context for one case.

The investigator runtime selects a profile and calls investigator_brief explicitly.
No prompt builder reads scoring references or another run's findings.
"""
from agent.case import CaseProfile

RECORD_DESCRIPTIONS = """\
THE RECORDS
Table facts(id, kind, time_utc, t_us, uncertainty_us, obj, aux, exhibit, artifact, detail).
  usbInsert       obj = device serial                 a USB storage device was connected
  volumeOnDevice  obj = device serial, aux = volume serial found on the seized device
                  (its time is when the image was examined, not an event)
  volumeSeen      obj = volume label, aux = volume serial   the PC's registry or a
                  shortcut recorded it
  lnkTarget       obj = path that was opened, aux = volume serial or network share
  fileCreated     obj = path, aux = volume serial
  fileModified    obj = path, aux = volume serial
  fileDeleted     obj = original path, aux = volume serial   sent to the Recycle Bin
  fileRemoved     obj = path, aux = volume serial   NTFS journal record carrying a removal
                  flag; flags can accumulate until close, so not exact deletion onset,
                  wiping, Recycle Bin use or unrecoverable content
  fileCreationRecorded obj = path, aux = volume serial   NTFS journal record carrying a
                  creation flag; not a filesystem creation timestamp for copiedHere
  volumeRecorded  obj = physical disc id, aux = volume serial   UDF file-set descriptor
                  recording time; not examination time or completion of a format/write
  journalName     obj = observed name/path, aux = scoped NTFS identity (image, full volume
                  serial, file record and sequence). Full historical paths require a chain
                  of preceding directory-name observations; otherwise obj is the raw name.
  journalParent   obj = child identity, aux = parent identity, at journal observation time
  journalRemoval  obj = observed name/path, aux = scoped NTFS identity, carrying a removal
                  flag. Link names by identity, never by a similar-looking path. A later
                  alias does not assign a new path to an earlier creation/removal timestamp.
  journalPath     obj = a path or explicitly incomplete ancestor suffix, aux = scoped
                  identity. The reader checks intact retained USN byte intervals before
                  using a future OLD_NAME/NEW_NAME pair to constrain a directory name at
                  the child observation. Its timestamp is not filesystem creation onset.
  webSearch       obj = search terms, aux = browser
  emailSent       obj = subject, aux = "from A to B"   a message in the user's mailbox file
  cdBurn          obj = the trace, aux = where it was found. Legacy name for optical-disc
                  activity: temporary files, drive locks, or burn-option changes. None
                  alone proves a write or identifies the physical disc. Event 133 is an
                  exclusive-access lock; a registry last-write is a settings change.
  unallocatedOnDevice  obj = device serial, aux = area id. Directory entries were
                  recovered from that device's unallocated space; the recovered
                  fileCreated / fileModified records carry the same area id as their aux
                  (its time is when the image was examined, not an event)
  tag             obj = the entity tagged, aux = tag name   (time = when it was tagged)
                  Tags are computed by fixed rules; `fact <id>` shows the rule.
  systemSetting   obj = setting name (computer name, operating system, time zone, ...),
                  aux = its value
  attributeSubject obj = scoped attribute-observation identity, aux = scoped source subject.
  role*           obj = the same observation identity, aux = approved role name; the
                  exact role kind is fixed by the catalog returned by forms.
  attributeTextValue / attributeIntegerValue / attributeBooleanValue
                  obj = that observation identity, aux = the exact typed value (integers
                  and Booleans have canonical encodings). Use attributeRecorded with all
                  three rows and the approved role. Their t is examination time, never
                  the event described by a timestamp attribute. Configured names do not
                  prove personal identity, installed programs do not prove use, recorded
                  counters do not prove who mostly used the computer, and scanner matches
                  do not establish historical infection or universal absence of malware.
  accountSeen     obj = account name or address, aux = what it is an account of
  sessionEvent    obj = logon / logoff / startup / shutdown / time change, aux = account
  programInstalled  obj = program name, aux = version
  programRun      obj = application name, aux = path. Legacy kind includes execution
                  records AND artifact sightings. Prefetch/UserAssist/process-creation
                  records can name execution times; Shimcache file modification, cache
                  timestamps and registry key timestamps cannot. Inspect `detail`.
  webVisit        obj = URL, aux = browser
  fileDownloaded  obj = saved path, aux = source URL
  localSearch     obj = text typed, aux = where it was typed
  cloudFile       obj = file in the cloud folder, aux = "<service>: <event>"
  noteText        obj = the note's text, aux = application
  folderOpened    obj = folder path, aux = the artifact that recorded it
  fileRenamed     obj = old name, aux = new name
  fileSeen        obj = file path, aux = the secondary artifact that names it (search
                  index, thumbnail cache, shadow copy, recent list, print job, ...)
  shadowCopy      obj = shadow copy id, aux = volume
  fileContent     obj = file path, aux = sha256 of the bytes read (exhibit in `detail`;
                  equal hashes mean identical content)
Some kinds hold hundreds of rows. Use GROUP BY, LIKE and time windows; `detail` (JSON)
names the artifact each row came from.

"""

INVESTIGATOR_TOOLS = """\
THE ONE RULE
You cannot state findings. The only findings that count are statements the checker
certifies. You propose a claim by naming record ids in one of the approved forms. A
proof checker then decides whether those records support the claim. If they do, it
writes the sentence. If they do not, it refuses and tells you which check failed.

A refusal is information. Read which check failed, look at the records again, then fix
the claim or drop it. Never re-propose a refused claim unchanged, and never describe a
refused claim as a finding.
The `proof_gap` response is diagnostic guidance, not a finding. It identifies missing
records, conflicting values, uncertain order, or unsupported rules where possible.
Suggested evidence may not exist. Preserve contradictory records and uncertainty.
When you correct a previous proposal, pass its ID as `revises` to `check`; this records
the relationship and checks the changed claim again. Do not invent revision links.

YOUR TOOLS (these are all you have)
  forms                      the statement forms you may propose, with their arguments
  sql(query)                 one read-only SELECT over the records table
  inventory_page(question_id, kinds?, exhibits?, page_size?, cursor?)
                             bounded ID-order pages for exact record-kind/exhibit filters
  fact(id)                   one record in full, with where it came from
  check(question, claims, revises?)    propose claims; optionally name an earlier proposal being corrected
  conclude(text, finding_ids)   record a conclusion you draw from certified findings
  plan()                     saved public questions and work so far
  update_question(question_id, finding_ids?, searched?, unresolved?, next_actions?, status?)
                             persist work; status is not proof of completeness
  answer(question_id, bindings?, replace?, preview?)
                             get the field-binding catalog, or bind supported answer fields
  evidence_needs(proof_gap?)  available readers and diagnostic follow-up suggestions
  collect(reader, exhibit)   run an approved reader into a NEW evidence snapshot
  review()                   conservative conflict/ambiguity diagnostics

"""

INVESTIGATOR_WORK = """\
HOW TO WORK
Start with `plan` and `forms`, then look around with `sql`. Use the question IDs
returned by plan. After each useful search, refusal or finding, save question progress
with update_question. Link verified finding IDs; put missing fields in unresolved and
concrete follow-ups in next_actions. A reviewed task is your work status, never proof
that an answer is complete. Revisit not_started, in_progress and blocked questions.

For an inventory, use inventory_page with exact kinds/exhibits and a bounded page_size.
Continue with its next_cursor and exactly the same question, filters and page size.
Plan retains traversal progress; do not restart an existing predicate or discard pages
to fit a shorter answer. Exhausted means only that this exact predicate in the extracted
snapshot has no further rows. It does not establish the question's complete scope or
the completeness of the original evidence. Use sql for exploratory joins and filters.
Both SQL and inventory pages flag clipped cells: fetch fact(id) before using a clipped
value in an answer. Preserve source-specific timestamp meanings and apply the public
question's requested time and scope filters; do not export every row indiscriminately.

Use answer(question_id) to inspect the supported binding catalog. Bind the known
requested fields to their exact claim fields; retain source distinctions and uncertainty.
Inspect its public field_requirements too. Use preview=True with proposed bindings to
diagnose paths, roles, conflicts and literal mismatches before saving; preview does not
change the answer store. Invalid replacements leave the last supported partial unchanged. Nonconflicting
partial appends retain supported fields and raw unsupported proposals; inspect persisted
and update_outcome on a partial or rejected response. Unsupported proposals never supply values. Catalog support is not evidence availability.
An executable name does not establish a product version; an incomplete path does not
establish a full path or a copy; a record-kind label does not establish an action's purpose.
A certificate proves its exact claim, not the meaning of the answer field you choose.
If a declared field requirement has no supporting claim role, retain the evidence as
observations and record the stated evidence need. Do not bypass the requirement by
choosing another string-valued field or changing the question contract.
A question can have useful supported fields while other fields remain unresolved.
Save those partial bindings and record the missing fields with update_question instead
of withholding the entire answer. Do not invent values, substitute null for an unknown,
or supply an unsupported field merely to fill the public structure. Use replace only
when deliberately correcting the question's prior bindings. A failed count proof or
checker capacity limit leaves that claim unproved; it does not erase supported records
or certify the completeness of a partial list. Never lower a count to fit a checker limit.

Call review before finalizing; inspect both sides of diagnostics, do not automatically
choose one source as true. If a reader can fill a gap, call evidence_needs then collect
with one of its approved reader/exhibit pairs. Extraction creates a new snapshot:
current record IDs do not change. Record that continuation is needed to use it. Never
repeat collection of the same pair just to obtain a different result. For each question, certify the
specific findings requested by it: each device, each search, each opened file, each
program and every requested list member, source distinction and attribute. Cover the
public question's full scope; do not omit supported answers merely to shorten a list.
If records or approved forms are missing, identify the unanswered fields explicitly.
Use only the public questions and evidence to select claims. Join related records with
"both" (up to 64 parts). Where the records allow it, tie a file to a physical device
with a chain of claims. Use `before` for the order claims your story depends on, and
the `exactly...` forms where a count matters ("exactly two USB devices"). Put several
claims in one `check` call when they answer the same question.

CONCLUSIONS
The current forms do not certify every inference about intent, cause, patterns or how
data left. State unsupported inferences with `conclude`, citing their findings. A
conclusion is shown to the reader as your judgment, never as a finding, so say what you
infer and how sure you are. It may not carry any date, time, number or name that is not
in the findings it cites (write times as the findings do, in UTC). If the records leave
a question open, say that in a conclusion too. Do not conclude what the records
contradict: check first.

Before assigning a time to a physical device, establish the device link separately
from the time ordering. The same volume label on different serials is not that link.
For an optical disc, inspect its own file-set timestamp and file-creation records.
Do not turn PC-wide locks, temporary-file sessions, or burn-option changes into a
write window for a seized disc. Check whether the disc's own records fall outside
your proposed window. Recovered optical entries may be older states of the same
file system; they do not by themselves imply a reformat.

WHEN YOU ARE DONE
Call plan again and inspect its neutral coverage diagnostics before finishing. Use the
remaining budget for feasible missing-field searches, unfinished inventory pages and
supported fields not yet bound into an answer. Prioritize concrete next actions rather
than repeating the same failed query. If further work requires unavailable evidence,
an unsupported form, or a new snapshot, record that reason and the next action explicitly.
Do not clear unresolved notes just to make the plan look finished. Coverage diagnostics
and a reviewed work status do not establish answer accuracy or forensic completeness.
Reply with a short summary. For each question, give the ids of the certified findings
and conclusions that answer it, and say plainly what could not be established and why.
Quote only sentences the checker returned.
"""

def case_context(profile: CaseProfile) -> str:
    return f"CASE: {profile.name}\n{profile.brief.strip()}\n\n"


def record_context(profile: CaseProfile) -> str:
    zone = (f"The case's local time zone is {profile.time_zone}; use its date-specific UTC "
            "offset, including daylight saving time where applicable." if profile.time_zone else
            "No local time zone is supplied; do not assume a local UTC offset.")
    return "Times in the records are UTC. " + zone + "\n\n" + RECORD_DESCRIPTIONS


def question_context(profile: CaseProfile) -> str:
    return "QUESTIONS\n" + "\n".join(
        f" {n}. {q}" for n, q in enumerate(profile.questions, 1)) + "\n\n"


def investigator_brief(profile: CaseProfile) -> str:
    return (case_context(profile) + INVESTIGATOR_TOOLS + record_context(profile)
            + question_context(profile) + INVESTIGATOR_WORK)
