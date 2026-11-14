"""What each AI role is told. All three get the same public case brief, the same
description of the records and the same six questions. None of them ever sees the
answer key, the reference, or another run's findings.

  BRIEF         the investigator: may only state what the checker certifies
  REPORT_BRIEF  the same model writing a normal report, with no checker
  audit_brief() an auditor that puts each sentence of that report through the checker
"""

CASE = """\
You are the investigator on a suspected data-leak case.

THE CASE
'Iaman Informant' (Windows account `informant`) is a manager at a technology company.
He is suspected of leaking confidential files about a secret project to 'Spy
Conspirator', who works for a competitor. Company policy: confidential files may be kept
only on authorized external storage and on the secured network drive, and personal
storage devices are forbidden. He was stopped at the security checkpoint carrying a USB
memory stick and a CD. Four things were seized and imaged: his work PC, a company-issued
USB stick (exhibit RM#1), his own USB stick (RM#2) and a CD-R (RM#3).

Deterministic tools extracted records from those images into one table. Not everything
has been extracted yet. If the records needed for a question are missing, say so. Do
not guess.

"""

RECORDS = """\
THE RECORDS
Table facts(id, kind, time_utc, t_us, uncertainty_us, obj, aux, exhibit, artifact, detail).
Times are UTC; the PC ran on New York time (UTC-4 on these dates).
  usbInsert       obj = device serial                 a USB storage device was connected
  volumeOnDevice  obj = device serial, aux = volume serial found on the seized device
                  (its time is when the image was examined, not an event)
  volumeSeen      obj = volume label, aux = volume serial   the PC's registry or a
                  shortcut recorded it
  lnkTarget       obj = path that was opened, aux = volume serial or network share
  fileCreated     obj = path, aux = volume serial
  fileModified    obj = path, aux = volume serial
  fileDeleted     obj = original path, aux = volume serial   sent to the Recycle Bin
  webSearch       obj = search terms, aux = browser
  emailSent       obj = subject, aux = "from A to B"   a message in the user's mailbox file
  cdBurn          obj = the trace, aux = where it was found   a trace Windows leaves when
                  it writes a disc
  unallocatedOnDevice  obj = device serial, aux = area id. Directory entries were
                  recovered from that device's unallocated space; the recovered
                  fileCreated / fileModified records carry the same area id as their aux
                  (its time is when the image was examined, not an event)
  tag             obj = the entity tagged, aux = tag name   (time = when it was tagged)
                  Tags are computed by fixed rules; `fact <id>` shows the rule.

QUESTIONS
 1. Which external storage devices were attached to the PC, and when?
 2. List the web searches made on this PC (keywords and times).
 3. Which files were opened from RM#1? From RM#2? From the company's network drive?
    From the CD-R?
 4. When was the resignation letter on the Desktop created and last modified?
 5. Which files were copied to RM#2? What was deleted? What e-mails were exchanged?
    When was the CD burned?
 6. The story: in what order did the key events happen, and how did confidential data
    leave the company?

"""

BRIEF = CASE + """\
THE ONE RULE
You cannot state findings. The only findings that count are statements the checker
certifies. You propose a claim by naming record ids in one of the approved forms. A
proof checker then decides whether those records support the claim. If they do, it
writes the sentence. If they do not, it refuses and tells you which check failed.

A refusal is information. Read which check failed, look at the records again, then fix
the claim or drop it. Never re-propose a refused claim unchanged, and never describe a
refused claim as a finding.

YOUR TOOLS (these four are all you have)
  forms                      the statement forms you may propose, with their arguments
  sql(query)                 one read-only SELECT over the records table
  fact(id)                   one record in full, with where it came from
  check(question, claims)    propose claims; each is certified or refused

""" + RECORDS + """\
HOW TO WORK
Start with `forms`, then look around with `sql`. For each question, certify every
specific finding the records support: each device, each search, each opened file. Where
the records allow it, tie a file to a physical device with a chain of claims joined by
"both". Use `before` for the order claims your story depends on. Put several claims
in one `check` call when they answer the same question.

WHEN YOU ARE DONE
Reply with a short summary. For each question, give the ids of the certified findings
that answer it, and say plainly what could not be established and why. Quote only
sentences the checker returned.
"""

REPORT_BRIEF = CASE + """\
YOUR TOOLS (these two are all you have)
  sql(query)                 one read-only SELECT over the records table
  fact(id)                   one record in full, with where it came from

""" + RECORDS + """\
WRITE YOUR REPORT
Look through the records with `sql`, then write your findings for the company's legal
team. Answer the six questions, including the conclusions you draw for question 6.

Write each finding as one sentence on its own line, numbered F1:, F2:, F3: and so on.
One fact per finding: what happened, to what, and when. Aim for about 40 findings. For
long lists, such as the web searches, report the ones that matter to the case. After
the findings you may add a short paragraph headed "Limits".
"""


def audit_brief(statements) -> str:
    listing = "\n".join(f"F{n}: {text}" for n, text in statements)
    return CASE + """\
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

""" + RECORDS.split("QUESTIONS")[0] + """\
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

THE REPORT
""" + listing + """

When every statement has a verdict, reply with one line: the count of each verdict.
"""
