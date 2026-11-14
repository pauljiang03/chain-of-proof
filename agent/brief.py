"""Shared record/tool instructions rendered with public context for one case.

BRIEF and REPORT_BRIEF retain the original public NIST context for legacy callers.
The investigator runtime selects a profile and calls investigator_brief explicitly.
No prompt builder reads scoring references or another run's findings.
"""
from agent.case import CaseProfile, LEGACY_PROFILE

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
  accountSeen     obj = account name or address, aux = what it is an account of
  sessionEvent    obj = logon / logoff / startup / shutdown / time change, aux = account
  programInstalled  obj = program name, aux = version
  programRun      obj = executable name, aux = path     a recorded run (`detail` says
                  which artifact, and whether the time is a run time)
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

YOUR TOOLS (these five are all you have)
  forms                      the statement forms you may propose, with their arguments
  sql(query)                 one read-only SELECT over the records table
  fact(id)                   one record in full, with where it came from
  check(question, claims)    propose claims; each is certified or refused
  conclude(text, finding_ids)   record a conclusion you draw from certified findings

"""

INVESTIGATOR_WORK = """\
HOW TO WORK
Start with `forms`, then look around with `sql`. For each question, certify the
specific findings that matter to it: each device, each search, each opened file, each
program used to move or remove data. You do not need to restate every row of a long
list; pick what an investigator needs, and join related records in one claim with
"both" (up to 64 parts). Where the records allow it, tie a file to a physical device
with a chain of claims. Use `before` for the order claims your story depends on, and
the `exactly...` forms where a count matters ("exactly two USB devices"). Put several
claims in one `check` call when they answer the same question.

CONCLUSIONS
Some things the checker can never certify: intent, cause, what a pattern means, how the
data left. State those with `conclude`, citing the certified findings they rest on. A
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
Reply with a short summary. For each question, give the ids of the certified findings
and conclusions that answer it, and say plainly what could not be established and why.
Quote only sentences the checker returned.
"""

REPORT_TOOLS = """\
YOUR TOOLS (these two are all you have)
  sql(query)                 one read-only SELECT over the records table
  fact(id)                   one record in full, with where it came from

"""

REPORT_WORK = """\
WRITE YOUR REPORT
Look through the records with `sql`, then write your findings for the case
reviewer. Answer all the questions supplied in this case profile.

Write each finding as one sentence on its own line, numbered F1:, F2:, F3: and so on.
One fact per finding: what happened, to what, and when. Aim for about 40 findings. For
long lists, such as the web searches, report the ones that matter to the case. After
the findings you may add a short paragraph headed "Limits".
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


def report_brief(profile: CaseProfile) -> str:
    return (case_context(profile) + REPORT_TOOLS + record_context(profile)
            + question_context(profile) + REPORT_WORK)


# Backward-compatible public constants for the original case and audit command.
CASE = case_context(LEGACY_PROFILE)
RECORDS = record_context(LEGACY_PROFILE) + question_context(LEGACY_PROFILE)
BRIEF = investigator_brief(LEGACY_PROFILE)
REPORT_BRIEF = report_brief(LEGACY_PROFILE)


def audit_brief(statements, only=None, profile: CaseProfile = LEGACY_PROFILE) -> str:
    """`only`: statement numbers to audit in this session; the rest of the report is
    given for context (a sentence may lean on the one before it)."""
    listing = "\n".join(f"F{n}: {text}" for n, text in statements)
    wanted = sorted(only) if only else [n for n, _ in statements]
    scope = ("Audit every statement." if not only else
             "Audit only these statements: " + ", ".join(f"F{n}" for n in wanted) +
             ". The others are there for context; do not record a verdict on them.")
    return case_context(profile) + """\
YOUR JOB
Another analyst wrote the report below from the same records. You are auditing it. For
every numbered statement, find out whether a proof checker will certify it.

You propose a claim by naming record ids in one of the approved forms. The checker
decides whether those records support the claim. If they do, it writes the sentence. If
not, it refuses and tells you which check failed.

YOUR TOOLS (these five are all you have)
  forms                      the statement forms you may propose, with their arguments
  sql(query)                 one read-only SELECT over the records table
  fact(id)                   one record in full, with where it came from
  check(question, claims)    propose claims; each is certified or refused
  record(statement, verdict, finding_ids, reason)   file your verdict on one statement

""" + record_context(profile) + """\
HOW TO AUDIT
For each statement, look up the records and propose the claim whose generated sentence
says the same thing. Then call `record` once for that statement, with one verdict:

  certified       certified sentences say everything the statement says, including its
                  times, its devices and its order of events
  weaker          only a weaker statement could be certified: "likely" where the report
                  states a fact, or the event without the device, order or person the
                  report asserts. Give the certified ids, and say in `reason` exactly
                  what the report claims that the certificates do not
  refused         the checker refused the claim that says this, or the records
                  contradict the statement
  no_records      the records contain nothing that bears on it
  cannot_express  the approved forms cannot say this kind of thing (an opinion, a
                  count, a kind of fact the forms do not cover). This is not a judgment
                  on whether it is true

Be strict and do not help the report. A statement is `certified` only if a reader of
the certified sentences alone would learn everything the statement asserts. If the
report states flatly something the records only suggest, that is `weaker`.

Take one statement at a time, and call `record` for it before you look at the next.
A verdict that is not recorded is lost if the session ends early.

THE REPORT
""" + listing + """

""" + scope + """
When each of them has a verdict, reply with one line: the count of each verdict.
"""
