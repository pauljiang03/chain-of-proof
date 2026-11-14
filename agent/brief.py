"""What the investigator is told. It gets the public case brief and the questions the
case asks. It never sees the answer key, the reference, or another run's findings."""

BRIEF = """\
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

THE RECORDS
Table facts(id, kind, time_utc, t_us, uncertainty_us, obj, aux, exhibit, artifact, detail).
Times are UTC; the PC ran on New York time (UTC-4 on these dates).
  usbInsert       obj = device serial                 a USB storage device was connected
  volumeOnDevice  obj = device serial, aux = volume serial found on the seized device
                  (its time is when the image was examined, not an event)
  volumeSeen      obj = volume label, aux = volume serial   the PC's registry recorded it
  lnkTarget       obj = path that was opened, aux = volume serial or network share
  fileCreated     obj = path, aux = volume serial
  fileModified    obj = path, aux = volume serial
  webSearch       obj = search terms, aux = browser
  tag             obj = the entity tagged, aux = tag name   (time = when it was tagged)

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
