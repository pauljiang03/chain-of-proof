# Optical inference review

The incorrect inference came from assigning host drive activity to a particular
disc without a physical-disc link, combined with templates that overstated what
optical records meant. The event-ID discrepancy is a separate issue. The original incorrect conclusion
is retained in a regression fixture. Git history retains the old reports.

## Independent raw evidence

The audit reads `data/pc.E01` directly and parses
`C:/Windows/system32/winevt/logs/System.evtx` with both `dissect.eventlog` and
`python-evtx`. Both parsers find provider `cdrom`, event **133**, qualifiers 16388:

| EVTX record | UTC on 2015-03-24 |
|---|---|
| 1412 | 19:47:47.657431 |
| 1416 | 19:56:11.965935 |
| 1425 | 20:24:46.429152 |
| 1428 | 20:41:21.884909 |

The event-log SHA-256 is
`cf1586aa80a7b2223120bb97675871164313c3a59a9fbb456246030dfe59b412`.
The source registry maps `cdrom` messages to `IoLogMsg.dll`. The image's English
resource `C:/Windows/System32/en-US/IoLogMsg.dll.mui` has SHA-256
`659e711af4d46d11181b1b815d15e9928a7b0f3450b3ae6ec6e4ec629cc75974`.
Its message `0x40040085` says: “Device %1 is locked for exclusive access.”

The reference prose prints 113. The bytes and two independent parsers support 133;
we did not change the extracted ID to fit the prose or silently amend the key.
The [audit JSON](../runs/current/audits/optical.json) retains the raw XML and hashes.
This discrepancy does not excuse the separate inference error: an exclusive-access
lock does not establish a completed write or which physical disc was present.
[Microsoft's API description](https://learn.microsoft.com/en-us/windows/win32/api/imapi2/nf-imapi2-idiscrecorder2-acquireexclusiveaccess)
also distinguishes acquiring access from writing media.

## Why C008 was unsupported

The original investigator conclusion C008 attributed an RM#3 write interval to
PC-side drive events and registry changes. The cited label was shared across volume
observations; a label is not a unique physical-device identifier. Its proposed window
also ended before the disc's own recorded file-set timestamp. Cited file creation
records were later still. Token checks accepted cited times without establishing
the relationship the sentence asserted.

RM#3's UDF file-set descriptor records `2015-03-24 20:53:17.880500 UTC`, volume
serial `AE88F176`. The canonical descriptor is at sector 52487; timestamp byte offset
107493392, raw hex `101fdf070318103511580500`. Multiple descriptor copies and nine
VAT states describe the same filesystem; they are not proof of nine formats.
This timestamp describes a recorded UDF field, not independently proven write
completion, wall-clock accuracy or user intent.

## Changes

- Optical trace templates now describe event 133 as an exclusive-access lock and
  registry activity as configuration. Neither is promoted to disc identity or a write.
- Same-label findings explicitly state that labels are nonunique. Recovery templates
  allow older states of the same filesystem instead of asserting a prior format.
- The reader exposes `volumeRecorded` from UDF descriptor bytes, distinct from an
  examination-time observation. `volumeRecordedAt` and `createdAfterVolumeRecord`
  certify that field and strict ordering on an identified volume, not formatting.
- A deterministic regression guard rejects the original C008 attribution/window.
  It works for other exhibit names but recognizes only limited sentence forms.
  Passing it is not a general inference proof.
- Default reports contain certified template sentences only. Free-form conclusions
  are available solely through `--include-judgments`, explicitly outside Lean.

The [regression fixture](../fixtures/optical_regression.json) preserves the original unsupported conclusion and its cited findings.
The current report uses corrected certificate sentences and excludes free-form judgments.

## Reproduce

```sh
python -m eval.optical_audit --out runs/dev/raw-optical-audit.json
python -m verifier.verify --run runs/current/run.json --facts evidence/case_facts.json
```

The independent raw audit also needs `python-evtx` and `pefile`.
No LLM judge is involved.
