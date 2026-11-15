# Source-grounded extraction gap triage

2026-11-14. Development diagnosis, not a benchmark rerun. No private answer key was consulted. Saved facts and measured runs were not modified. Source: `/Users/paul/Documents/hackpton/data/pc.E01`; frozen derived snapshot: `/private/tmp/cop-nist-ready-20261114T224105Z/facts.json`.

## Confirmed source-present omissions

Direct registry reads through the existing `dissect.target.Target` reader establish:

| Public question | Actual artifact/value | Diagnosis and change |
|---|---|---|
| Q3 | SOFTWARE `Microsoft\Windows NT\CurrentVersion`, `SystemRoot=C:\Windows` | Parsed-field omission. Export a `systemSetting` row with exact registry-value provenance. |
| Q4 | Selected `Eastern Standard Time` definition under SOFTWARE `Microsoft\Windows NT\CurrentVersion\Time Zones`, `Display=(UTC-05:00) Eastern Time (US & Canada)` | Parsed-field omission. Export source Display/Std/Dlt from the selected definition, without synthesizing a label from offsets. |
| Q42 | SOFTWARE `Microsoft\Windows Search`: DataDirectory, DefaultDataDirectory, SetupCompletedSuccessfully | Parsed-field omission. Preserve raw environment-variable paths; do not pretend expanded locations were independently observed. |
| Q42 | SYSTEM selected `ControlSet001\Services\WSearch`: Start=2, DelayedAutoStart=1, ImagePath | Parsed-field omission. Preserve service configuration; this does not prove historical runtime state. |
| Q50 | SYSTEM `ControlSet001\Control\BackupRestore\FilesNotToSnapshot`, OutlookOST=`$UserProfile$\AppData\Local\Microsoft\Outlook\*.ost` | Parsed-field omission, rather than unavailable source evidence. Preserve the source multi-string value. |

The small `extractor/system.py` change exports these as existing `systemSetting` records. Generic configuration rows use the fully qualified registry path and value name in obj, and the source value in aux (string verbatim, integer decimal, or compact deterministic JSON for a string list). Typed `registry_value`, `registry_path`, and `registry_value_name` provenance retains the original representation. No fact schema, proof template or answer projection was changed. The existing settingRecorded form can express these source-bound name/value observations; question-specific projection and complete answer coverage remain separate work.

An actual-image **settings-only** spot check (partition and network sweeps disabled) emitted 11 added rows. No full extraction was run. Synthetic alternate drive, selected ControlSet002, Pacific timezone, missing key, zero integer and multi-string tests pass; the existing 16 system tests pass. Readiness environment lacks pytest; tests were run directly and through unittest.

## Mail: body omission is confirmed; complete addressing is not

Using the existing pypff binding from the repository virtual environment, a read-only metadata-presence walk of the original OST found the same 11 subject-bearing, submit-time-bearing messages outside Sync Issues as the frozen extraction. One exposes a plain-text body; ten expose HTML bodies. All eleven expose display-To; six expose sender SMTP (0x5D01). Total attachments reported by those messages is zero.

`extractor/windows.py::_email` exports sender availability, subject, message ID, folder and attachment count, but never reads or exports body properties. Therefore bodies are a confirmed reader omission, not absent from these source messages. Display-To is not necessarily a complete SMTP recipient list. This inspection did not establish recipient-table recovery or missing sender-address alternatives. No new mail implementation or unsupported address guessing was added. Indexed mail versus OST remains a separate source-specific inventory problem; the Windows.edb unclean-shutdown limitation still applies.

## DOCX: existing size, omitted embedded metadata

Frozen fact 125 already records the resignation document's size as 11,893 bytes; fact 12707 records its content. Directly reading the live file at `C:/Users/informant/Desktop/Resignation_Letter_(Iaman_Informant).docx` confirms 11,893 bytes. Thus a missing answer size is an export/assembly issue for this file.

Its existing ZIP `docProps/core.xml` contains created `2015-03-24T18:32:00Z` and modified `2015-03-24T18:59:00Z`. The current content reader identifies/hash-reads the document but does not export OOXML core metadata. This is a confirmed parsed-field omission. Embedded core timestamps are distinct from NTFS STANDARD_INFORMATION and FILE_NAME timestamps. No claim is made here that all required FILE_NAME timestamp fields were validated, nor that embedded metadata establishes the real authoring event. No content-reader change was included.

## Coverage and assembly versus evidence gaps

Literal pilot outputs under `runs/dev/sol61-ablation-20261115T010310Z/evaluation/C/answers.json` explicitly report existing inventories not assembled for Q12 (334 session rows), Q27 (network artifacts), and Q16 (85 searches, with a verified census). Q11 (518 program rows) and Q15 (747 web rows) additionally hit the checker's 500-record census cap, confirmed in `/private/tmp/cop-sol61-ablation-20261115T010310Z/public/C/bridge-calls.jsonl`. These are assembly or checker-capacity issues, not source absence; they are outside this reader-only fix.

Q23's 45 certified rename observations are not themselves proof of complete historical Desktop membership. Physical-device identity, burn completion, wiping methods and intent similarly require supported relationships; adding raw registry values does not solve them.

## Next bounded work

1. Integrate the configuration reader fix, then regenerate a separately named snapshot only when authorized. Existing measured scores do not change.
2. Add a supported projection for source-bound settings rather than treating all generic registry values as proved answers.
3. A separate small mail change could preserve body format/content with explicit availability, and an OOXML metadata reader could preserve core timestamps with their own semantics. Both need focused tests and size/encoding bounds before use.
4. Complete deterministic, source-specific inventory assembly and correct local-time filtering. Revisit census capacity independently of extraction.

No new ESE recovery engine, thumbnail interpretation, Lean schema expansion, full image extraction or model trial was performed.
