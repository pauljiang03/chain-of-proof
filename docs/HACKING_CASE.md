# NIST CFReDS Hacking Case

This package uses the [official NIST Hacking Case](https://cfreds-archive.nist.gov/Hacking_Case.html).
It contains all 31 public questions. It is separate from Data Leakage and from the DFIR Madness case.
The image contains fictional training data.

## Prepare the evidence

Install the project and the extraction extra. Use a separate environment if another experiment is running.
Download the public image with this command:

```sh
python scripts/fetch_hacking_case.py data/hacking_case
```

The command downloads both E01 segments and the public acquisition log.
It does not download the answers. It records source URLs, sizes, and SHA-256 values.
The image files stay outside Git. The downloader preserves existing files.
A download hash identifies container bytes. It is not the acquired disk hash.

Create a new evidence snapshot:

```sh
python -m app.cli ingest \
  --images data/hacking_case \
  --exhibits eval/hacking_case/exhibits.json \
  --title "NIST CFReDS Hacking Case" \
  --readers windows,system,webcloud,filetraces,inventory,content,hacking,host_attributes,image_integrity \
  --out runs/dev/hacking-evidence
python -m eval.readiness \
  --questions eval/hacking_case/questions.json \
  --facts runs/dev/hacking-evidence/facts.json \
  --out runs/dev/hacking-readiness.json
```

Use a new output path on each run. Read `health.json` before you assess coverage.
The readiness report is not an accuracy score. A supported role can still have no useful evidence.

## What the readers provide

| Source | Retained observations |
|---|---|
| E01 logical image and checksum section | Full-stream MD5, SHA-1, SHA-256; separate stored acquisition digest |
| Windows registry and SAM | OS, install time, timezone, owner text, computer/domain settings, accounts, counters, network descriptions |
| Legacy application files | Exact setup fields, mail/news settings, IRC settings and logged channels, byte and line locations |
| PCAP traffic | Bounded TCP reconstruction, HTTP request fields, source packet locations, conflicting-fragment refusal |
| Browser files | Cache filenames, literal email text, supported history records |
| INFO2 and NTFS | Original recycle paths, retained files, allocation/deletion flags, scoped file counts |
| Local ClamAV scan | Scanner and signature database identity, copied-file hashes, detections, omissions and errors |

The readers also support the `Documents and Settings` layout used by Windows XP.
They do not execute programs from the image.

## What a proof means

A typed attribute has three linked records: source subject, fixed role, and typed value.
Lean checks the record kinds, common identity, and requested role.
A claim cannot change an email setting into a captured-traffic address.
Integer and Boolean values use dedicated types. They are not inferred from arbitrary text.

The image comparison rule requires the same image subject and algorithm on both sides.
It compares the stored acquisition digest with the recomputed logical-image digest.
A missing stored digest leaves the comparison unanswered. Matching digests do not prove acquisition authenticity.

The public answer schema declares the allowed meaning of each answer field.
The report keeps examiner judgments separate from certified source observations.
The formal checker does not prove that the source is truthful, the parser is complete, or the investigator selected the right evidence.

Some questions need stronger relations. A retained logon counter does not establish habitual use.
A MAC vendor prefix alone does not prove which interface was used during setup.
A User-Agent header can be false. A retained newsgroup mailbox does not by itself prove subscription.
The tool must state these limits and identify the additional evidence or rule it needs.

## Optional antivirus scan

Install ClamAV and update its official signature database with `freshclam`.
Set `COP_CLAMAV_DATABASE` to the local signature directory.
Select the `antivirus` reader explicitly. It does not install software, download signatures, or start a service.

```sh
COP_CLAMAV_DATABASE=/path/to/clamav-database \
python -m app.cli ingest \
  --images data/hacking_case \
  --exhibits eval/hacking_case/exhibits.json \
  --title "NIST CFReDS Hacking Case: allocated-file scan" \
  --readers antivirus --out runs/dev/hacking-scan
```

The scan reads allocated regular files. It excludes links, alternate streams and deleted or unallocated data.
File size, total size, file count and time limits are explicit in the reader.
The scanner reads numbered copies with no execute permission. It does not change the image.
The report retains skipped files and scanner errors. A partial scan cannot produce a negative complete-scope result.
A signature match can be a false positive. No detections do not prove that no malware exists.
See the [ClamAV scan documentation](https://docs.clamav.net/manual/Usage/Scanning.html).

## Run and score

Give the investigator only the facts, `eval/hacking_case/case-profile.json`, and `eval/hacking_case/questions.json`.
Use the same model, public contract, evidence and budget for each comparison arm.
Freeze these inputs before the run. Keep the private reference outside the investigator's tools.
Use the existing investigation, report and independent verification commands.

The private evaluator uses `eval/hacking_case/reference.json` only after the run ends.
It compares typed answers with fixed rules. It does not ask an agent to judge prose.
Questions that request N examples accept exactly N distinct entries from the declared source pool.
Unrequested pool alternatives do not count as missing. Duplicate, unsupported and excess entries do not receive full credit.

Report complete, partial, unanswered and incorrect questions separately.
Report certificate verification separately from answer accuracy.
Do not combine the 31-question denominator with another case or claim 100% support from a successful extraction alone.
