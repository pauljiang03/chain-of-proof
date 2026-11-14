# Chain of Proof

**Machine-checked digital forensics: the LLM proposes, Lean 4 decides.**

An AI forensic investigator whose report contains only findings that a proof checker has
accepted. LLM agents and a brute-force miner search a disk image for findings. Each
finding is written in a small Lean 4 intermediate representation and checked by the Lean
kernel against facts that deterministic forensic tools extracted from the image. A
finding that fails the check never reaches the report. One that passes comes with a
certificate: the artifacts it cites, the rules it assumes, and a proof anyone can re-run.

Built at HackPrinceton Fall 2026. Full design: [chain-of-proof-revised.md](chain-of-proof-revised.md). Who does what: [TASKS.md](TASKS.md).

## Status

| Piece | State |
|---|---|
| Lean core: facts, brick IR, checker, sets, theorems about the checker | Working, tested |
| `check`: claim JSON → Lean certificate → kernel verdict, with per-brick feedback on rejection | Working, tested |
| Verifier: re-check a certificate from the evidence DB alone | Working, tested |
| Extractor: the real PC and USB images → evidence file (`extractor/`) | Working for USB devices, volumes, shortcuts, jump lists, web searches, file times, Recycle Bin records, CD-burn traces, e-mail, and file records left on a formatted USB stick. Not yet: the CD-R image, purged e-mail, and the rest of the answer key (see Evaluation) |
| Miner (`miner/`): every instance of the approved sets, no LLM | Working on the real evidence |
| Scorer against the NIST answer key (`eval/`) | Working; numbers below |
| AI investigator (`agent/`): an LLM with four tools and no file or shell access | Working on a Claude Code login; one scored run. The API backend (LangChain deepagents) is written but has not been run |
| UI | In progress (see [TASKS.md](TASKS.md)); `ui/public/run.json` is a real run |

The numbers in this README come from the real case images, not from a fixture.

## The idea

An LLM is good at searching evidence and bad at being trusted. A proof checker is the
reverse. Chain of Proof puts a formal language between them.

```
search (untrusted)                 claim (Lean IR)              check (trusted)
LLM agents, brute-force miner ──►  bricks citing fact ids  ──►  Lean kernel
                                          ▲
                 facts extracted from the image by deterministic tools
```

- **Search is fuzzy, so untrusted components do it.** They can be wrong, creative or buggy.
- **Checking is exact, so Lean does it.** A claim either follows from the cited facts or it doesn't.
- **The certificate sits between them.** It can be re-checked without repeating the search.

## Problem setting

A digital forensic examiner receives disk images and must answer questions such as
"which device received the confidential files, and when?" The answer is a chain of small
inferences across artifacts: a USB device serial in the registry, a volume serial that
maps to it, a shortcut file that points at that volume, file timestamps, a browser
history entry. Each link is easy to state and tedious to verify. The conclusions feed
legal proceedings, regulatory responses and decisions about people's jobs.

We work on the [NIST CFReDS Data Leakage Case](https://cfreds-archive.nist.gov/data_leakage_case/data-leakage-case.html):
a Windows 7 PC and three removable media in an insider data-theft scenario, with a
[published answer key](https://cfreds-archive.nist.gov/data_leakage_case/leakage-answers.pdf).

## Motivation

- **Investigators cannot rely on LLM output as it stands.** One fabricated timeline entry
  or wrong attribution can send people after the wrong suspect.
- **Existing LLM forensic agents check less than they appear to.** The strongest open
  agent we know of, [Mulder](https://pypi.org/project/mulder-dfir/), requires every finding
  to cite a real tool call and rejects findings that cite nonexistent ones. That shows a
  citation exists. It does not show the cited evidence supports the sentence. On this
  same case its best published configuration still states claims the answer key
  contradicts (see [Benchmarks](#benchmarks)).
- **The idea of forensic certificates is not new, but automating it is.**
  [Certificates for Verifiable Forensics](https://reed.cs.depaul.edu/cpitcher/research/2014-csf-certificates-for-verifiable-forensics.pdf)
  (IEEE CSF 2014) proposed certificates as the artifact between search and verification
  and formalized one case in Coq by hand. We generate the certificates automatically.

## Solution

### Pipeline

```
disk image ─► extractor (TSK / plaso / parsers) ─► evidence DB (DuckDB): facts + provenance
                                                        │
                    ┌───────────────────────────────────┤
                    ▼                                   ▼
          brute-force miner (Lean)              LLM agents (read-only SQL)
                    │      candidate claims             │
                    └───────────────┬───────────────────┘
                                    ▼
                      check(): claim JSON ─► Lean file ─► kernel
                                    │
                 rejected ◄─────────┴─────────► verified: certificate
                 (per-brick reasons                (cited facts, rules, proof,
                  go back to the agent)             English from templates)
```

### The IR

A **fact** is one row from the extractor: `id, kind, t, res, obj, aux`. Strings are
interned to numbers, times are UTC microseconds, and `res` is the timestamp's uncertainty.

A **claim** is built from four primitive bricks and one connector
([`Claim.lean`](lean/ChainOfProof/Claim.lean)):

| Brick | Checks |
|---|---|
| `is f k` | fact `f` has kind `k` |
| `val f s v` | a slot of `f` equals a constant (used for tag ids) |
| `link a sa b sb` | two facts hold the same entity in the named slots |
| `before a b` | `a` happened before `b` by more than both timestamp uncertainties |
| `both c d` | both claims hold |

**Sets** are named compositions of bricks, one per forensic rule
([`Sets.lean`](lean/ChainOfProof/Sets.lean), [`Rules.md`](lean/ChainOfProof/Rules.md)).
For example, "USB device was connected and mounted as volume V":

```lean
def usbMountedAs (u m : Nat) : Claim :=
  .both (.is u .usbInsert) (.both (.is m .volumeMount) (.link u .obj m .obj))
```

Agents propose set instances as JSON. A certificate is a generated Lean file:

```lean
def cited : List Fact := [
  ⟨4512, .usbInsert,   1427119200000000, 1, 101, 0⟩,
  ⟨4513, .volumeMount, 1427119201000000, 1, 101, 88⟩,
  ⟨4600, .lnkTarget,   1427120900000000, 1, 913, 88⟩ ]

def claim : Claim := .both (Sets.usbMountedAs 4512 4513) (Sets.openedFromMount 4600 4513)

theorem verified : holds cited claim = true := by decide +kernel
```

### What keeps it honest

| Property | How |
|---|---|
| The agent cannot write Lean | It writes claim JSON with fact ids only. `checker/` generates the Lean text and reads the cited rows from the evidence DB itself. |
| The sentence shown is the sentence checked | English comes from a fixed template per set, filled from the cited facts. No LLM writes report text. |
| Two statements are linked only if the evidence links them | Claims carry fact ids, never raw values. Joins are `link` bricks or shared facts. |
| A certificate rests on the kernel alone | `holds` is written so that `#print axioms` reports no axioms for a certificate. |
| A certificate can be re-checked later | `verifier/` rebuilds the Lean file from the DB rows, re-runs the kernel, and compares row hashes and the English. |
| Weak links are visible | Each finding carries the rules it used and a strength: `strong`, `heuristic` (e.g. the copy signature), or `judgment` (an LLM-assigned tag). |

### What Lean adds over a checker script

For a single claim, the kernel does the same work a short Python function could. Lean
earns its place through statements proved once about the checker itself
([`Theorems.lean`](lean/ChainOfProof/Theorems.lean)):

| Theorem | Meaning |
|---|---|
| `before_trans`, `before_asymm` | Certified order is transitive and never runs both ways, even across file systems with different timestamp resolution. A certified timeline cannot contradict itself. |
| `holds_mono`, `holds_append` | A certified finding stays certified when more evidence is added. |
| `holds_both` | Proven bricks snap into a proven larger claim without re-checking. |
| `mine_sound` | Whatever the brute-force miner emits holds, whatever its generators do. |
| `usbMountedAs_sound` | A certified set instance implies the plain-language condition it stands for. |

### What a certificate does and does not show

A certificate shows that the cited facts satisfy the claim under the listed rules. It
does not show:

- **that the extractor parsed the image correctly.** Extraction is trusted and
  re-runnable. Re-deriving cited facts from raw image bytes is a stretch goal.
- **that a rule is true of Windows.** Rules are stated assumptions with strength labels.
- **that nothing else happened.** Claims are positive. There is no brick for "no other
  device was connected", so a competing explanation that fails to certify is unproven,
  not refuted.
- **who was at the keyboard.** Artifacts identify accounts and devices.

## Benchmarks

### Baseline on the same case

Mulder publishes item-by-item scores for this case against 20 ground-truth items from
the NIST answer key ([source](https://pypi.org/project/mulder-dfir/), v1.5.11; median of
three runs, range in parentheses):

| Model | Full match | Detection | False positives | Runtime per run |
|---|---:|---:|---:|---:|
| Claude Opus 4.6 | 45% (45–50) | 95% (90–95) | 10% (5–10) | 68–79 min |
| Kimi K3 | 35% (35–50) | 90% (80–95) | 20% (20–25) | 52–70 min |
| GLM-5 | 20% (20–25) | 75% (75–90) | 20% (10–25) | 60–63 min |

Full match means the exact fact is stated, detection means related evidence was found,
and a false positive is a claim the answer key contradicts.

The number we target is the false-positive column. Coverage will be lower than
Mulder's: we certify only what the IR can express.

**Our own reading against Mulder's 20 items.** Not a like-for-like score: the item
labels are paraphrased from Mulder's published scorecard
([Opus run 1](https://github.com/calebevans/mulder/blob/main/examples/ndlc-v1.5.2/opus-4.6-run1/ACCURACY-REPORT.md)),
we marked our own output, and nobody has audited the marking (TASKS.md, lane 4).
"Stated" means a certified finding says the exact fact.

| | Mulder, Claude Opus 4.6 (published, median of 3 runs) | Chain of Proof (self-marked, 1 run) |
|---|---:|---:|
| Items stated exactly | 45% (45–50), 9 of 20 | 35%, 7 of 20 |
| Items with at least related evidence | 95% (90–95), 19 of 20 | 75%, 15 of 20 |
| Claims the answer key contradicts | 10% (5–10), 1 to 2 claims per run | none found; 24 of 24 known-false claims refused |
| Time per run | 68 to 79 min | 4 min for the AI run, 45 s for the miner |
| Each sentence can be re-checked from the evidence | no | yes |

| Mulder item | Ours | What our certified findings say |
|---|---|---|
| 3, 4. The two USB sticks: serial, label | Stated | Serial, label and connection time; not the file system type |
| 9. Searches show premeditation | Stated | All 28 searches of the answer key, with times |
| 11. iCloud installer downloaded | Stated | `icloudsetup.exe` created in Downloads |
| 12. USB connection times | Stated | From the device install log and registry, not the event log |
| 17. Files opened on RM#2 | Stated | Both answer-key rows |
| 19. E-mail with the outside contact | Stated | 11 of the 12 messages |
| 6. Five project documents on USB | Partly | The five files on RM#1 and their copy signature (heuristic) |
| 7. Files disguised on RM#2 | Partly | 17 recovered names; 4 match a confidential file's size and modified time |
| 8. CCleaner and Eraser | Partly | The searches for them; not their installation or use |
| 10. Google Drive installed | Partly | The installer download and the search |
| 13. Bulk copy on Feb 15 | Partly | Creation times of the five files on RM#1 |
| 15. Files removed from RM#2 | Partly | Their records in unallocated space; the format is not stated |
| 18. Network folders browsed | Partly | Files opened on the share; not the folders |
| 20. FAT time zone | Partly | Applied and recorded on each row; not a finding |
| 1. Suspect identity | No | |
| 2. Operating system | No | In the extractor's metadata only |
| 5, 16. The CD-R: format, contents | No | The CD image is not read |
| 14. CCleaner run without cleaning | No | |

### Checker performance (measured)

Apple Silicon laptop, Lean 4.35.0, core library only.

| Measurement | Result |
|---|---:|
| One certificate, process start to verdict (`lake env lean`) | 0.16 s |
| `check()` end to end, verified claim | about 0.3 s |
| `check()` end to end, rejected claim with per-brick feedback | about 0.5 s |
| 200 independent bricks in one file | 0.29 s |
| 1,000 independent bricks in one file | 0.81 s |
| 5,000 independent bricks in one file | 3.64 s |
| One claim over 200 cited facts (199 chained `before` bricks) | 0.6 s |
| Axioms a certificate depends on | none |

Consequences for the design: a warm Lean server is not needed for live checks, and
every mined brick can be kernel-checked rather than left at a weaker tier. One limit:
plain `decide` exceeds its recursion limit near 200 cited facts in one claim, so
certificates use `decide +kernel`.

### Results on the real case images

One command, no LLM, about 45 seconds: `python3 -m eval.baseline`. It mines every
instance of the approved sets from the extracted evidence, sends each through the Lean
kernel, and scores the result against 96 rows of the NIST answer key.

| Check | Result |
|---|---|
| A. Answer-key rows found in the extracted evidence | **95 / 96**; all 95 within 2 s of NIST's timestamp |
| B. False claims (per the answer key) refused by the kernel | **24 / 24** |
| B. True claims (per the answer key) certified | 21 / 22 |
| C. Answer-key rows stated by a certified finding | **90 / 96** |
| Certified findings | 179: 124 strong, 55 heuristic, 0 judgment |
| Certificates that re-verify from the evidence file alone | 179 / 179 |

| Answer-key question | Rows | In evidence | Certified |
|---|---:|---:|---:|
| Q16 web searches | 28 | 28 | 23 |
| Q21 e-mails | 12 | 11 | 11 |
| Q22 USB devices attached | 4 | 4 | 4 |
| Q26 files opened on RM#2 | 2 | 2 | 2 |
| Q28 files opened on the network drive | 4 | 4 | 4 |
| Q33 CD burns | 5 | 5 | 5 |
| Q35 files opened from the CD-R | 8 | 8 | 8 |
| Q36 resignation letter timestamps | 2 | 2 | 2 |
| Q51 Recycle Bin | 14 | 14 | 14 |
| Q55 files copied to RM#2 | 17 | 17 | 17 |

**With the AI investigator** (`python3 -m agent.run`, one run, Claude Opus through
Claude Code, 228 seconds, 43 tool calls):

| | Miner (no LLM) | AI investigator |
|---|---:|---:|
| Claims proposed | 179 | 286 |
| Certified by the kernel | 179 | 285 |
| Refused by the kernel | 0 | 1 |
| Answer-key rows stated by a certified finding | 90 / 96 | 95 / 96 |
| ... of the 95 rows present in the evidence | 90 | 95 |
| Certificates that re-verify from the evidence file alone | 179 / 179 | 285 / 285 |

The investigator was given the case brief and the case's questions, never the answer
key: it has four tools (`forms`, `sql`, `fact`, `check`) and no access to files or a
shell. It certified every answer-key row the evidence holds.

The one refusal was a wrong claim, not a malformed one. The investigator claimed the
zip was opened from the volume now on the seized RM#2. Refused,
`FAIL link 41 (aux) 375 (aux)`: the shortcut names volume `9E6A5B82`, the seized stick
holds `B4D85399`. It then certified what the records do support, the same-label link,
which is heuristic and says so. This is the claim a fluent report gets wrong: the
stick was reformatted, so "opened from RM#2" is an inference, not a record.

An earlier run on a previous build of the evidence had two refusals of the same kind:
a copy claimed for a file modified after it was created, and two events claimed in the
wrong order (31 minutes apart; the investigator then certified the right order).

Its closing summary ([`runs/investigator/summary.md`](runs/investigator/summary.md))
lists what the records cannot show: that both volumes are the same physical stick,
that the files on RM#2 have the confidential files' contents (only size and
last-modified time match), what the burns wrote, and that the volumes labelled
`IAMAN CD` are the seized disc. One run only; LLM runs vary.

What the table says: where we extract an artifact, it agrees with NIST to the second.
The one row not in evidence is an e-mail purged from the mailbox, which the mailbox
library's Python interface cannot recover. The five searches in evidence but not
certified by the miner are the ones its watch list does not flag.

Three of these come from places a normal file listing does not reach:

- **Files copied to RM#2.** The stick was quick-formatted and lists no files. Its old
  folder clusters are still there: 41 file records in 8 folders, among them all 17 files
  NIST names, created 09:59:27 to 10:00:18 local time, one minute after the stick was
  connected. The folder that held them was named in the overwritten root directory, so
  its path reads `\[lost folder 3]\design\...`; nothing is guessed.
- **The disguised files.** Four of the recovered records have exactly the size and
  last-modified time of four confidential files on RM#1: `winter_whether_advisory.zip`
  is 16,381,123 bytes, modified 2014-12-16 16:10:26 UTC, and so is
  `[secret_project]_detailed_design.pptx`. NIST's answer key pairs the same files. The
  extractor tags such pairs; the tag says contents were not compared. Getting here
  needed one correction: Windows writes FAT times with the UTC offset in force when it
  writes, so a December time written in March is 4 hours from UTC, not 5. Our first
  build was an hour off on these 17 modified times. The plain-report run noticed the
  constant one-hour gap, which is how we found it.
- **Recycle Bin.** It was emptied. The 14 index files are deleted, but each still sits
  inside its file-table record with the original path and deletion time.
- **CD burns.** Three independent traces: the burner's temporary files in the NTFS
  change journal, the `cdrom` driver's event 133, and the user's CD Burning settings.
  A finding built on them is labeled heuristic: they show a disc was written, not what.

**The one true claim the gate refuses is the most useful result so far.** NIST says
`winter_whether_advisory.zip` was opened from the suspect's own stick, RM#2. The
shortcut records volume serial `9E6A5B82`. The seized RM#2 holds volume `B4D85399`,
because the suspect quick-formatted it afterwards. Lean refuses "opened from the seized
RM#2" as a strong claim, correctly: no record links those two serials. The registry
does show both volumes under the label `IAMAN $_@`, so the miner certifies the same
conclusion as a *heuristic* finding that names the weak link (rule R8, shared label).
An LLM report would state the conclusion flat. Ours shows where the inference is.
The recovered folder records now add a second, independent line: a record for
`winter_whether_advisory.zip`, created 09:59:37, sits in the unallocated space of the
seized RM#2 itself (strong, rule R13), 106 seconds before the shortcut shows a file of
that name being opened.

Our 96 rows and Mulder's 20 items measure different things; the self-marked table under
[Baseline on the same case](#baseline-on-the-same-case) is the closest comparison so far.

## Evaluation

The scorer has no LLM in it. Same evidence, same reference, same run: same numbers.

**Reference.** [`eval/reference.json`](eval/reference.json): 96 rows transcribed from
the [NIST answer key](https://cfreds-archive.nist.gov/data_leakage_case/leakage-answers.pdf),
each with its question number, page, NIST's local time and the UTC conversion. It
covers every answer row of ten questions about the leak itself (searches, e-mails,
devices, opened files, CD burning, the resignation letter, deleted files, files copied
to RM#2). The list was fixed before the first scored run and includes the rows we
cannot produce yet.

**Three checks**, all in `python3 -m eval.score`:

| Check | Question it answers | How |
|---|---|---|
| A. Extraction | Is the evidence right? Lean cannot check this. | For each reference row: is there a fact of that kind, for that entity, within 2 s of NIST's time? Reported as match, time differs, or missing. |
| B. Gate | Does the kernel separate true from false? | [`eval/labeled_claims.json`](eval/labeled_claims.json): 22 claims the answer key supports and 24 it contradicts. True ones must certify, false ones must be refused. |
| C. Run | How much of the answer key does a run certify? | A row counts only if a verified finding *states* it: the fact is an argument of a set whose sentence prints its entity and time. Citing it through a tag does not count. |

**What is deterministic, and what is not.**

| Stage | Deterministic? | Check |
|---|---|---|
| Extractor | Yes | Two builds from the same images give the same file (`sha256` recorded in `eval/results.json`) |
| Miner | Yes | Finding ids and claims depend only on the evidence file (tested) |
| Kernel verdict | Yes | A certificate either type-checks or does not |
| Scorer | Yes | Pure function of three JSON files |
| LLM agents | No | Scored by the same scorer; report the range over several runs. The miner run is the fixed floor to compare against. |

**Claims we are testing.**

1. *No certified finding is contradicted by the answer key.* Check B is the direct
   test: every false claim must be refused. A single acceptance falsifies it.
2. *The check does real work.* The 24 refusals name the failing brick, e.g.
   `FAIL link 41 (aux) 241 (aux)`: the shortcut's volume is not the device's volume.
3. *The IR covers enough to matter.* Check C, per question, with the misses listed.

**What this evaluation does not show.** The reference covers ten of the answer key's
57 questions. The rows were transcribed by hand. Agreement with NIST on 95 rows says
nothing about facts the reference does not mention. The extractors for e-mail, the
Recycle Bin, CD burns and RM#2 were written after the first scored run, with the answer
key's method notes open: they show that we read the artifacts NIST names and get NIST's
values, not that we would have found them unaided. Rules R1 to R13 are assumptions about
Windows, listed on every certificate, not proved.

**Tests in this repo** (`tests/`, 26 cases; most run the real kernel): the ten checker
and verifier cases on the fixture (golden certificate with no axioms, tagged narrative,
five kinds of rejection, malformed claims, tampering, DuckDB backend); four on the
real evidence (extraction still matches the answer key, the gate refuses every labeled
false claim, the miner is deterministic, a row is only credited when stated); eight on
the investigator's tools and the report audit (read-only SQL, refusals that name the
values that disagree, no duplicate logging, a verdict counts only with a certificate
behind it); and four on recovering FAT directory entries and converting their times, on bytes
built in the test.

## Quickstart

Requires [elan](https://github.com/leanprover/elan) (Lean 4) and Python 3.9+.

```bash
cd lean && lake build && cd ..

# check a claim against the sample fixture
python3 -m checker.check --facts fixtures/sample_facts.json --id F7 \
  --claim '{"both": [{"usbMountedAs": [4512, 4513]}, {"openedFromMount": [4600, 4513]}]}'

# a claim the facts do not support: rejected, with the failing brick named
python3 -m checker.check --facts fixtures/sample_facts.json --id F8 \
  --claim '{"both": [{"usbMountedAs": [4510, 4511]}, {"openedFromMount": [4600, 4511]}]}'

# re-check a stored certificate from the evidence alone
python3 -m verifier.verify fixtures/sample_cert/N1.json --facts fixtures/sample_facts.json

# the real case: mine, kernel-check and score against the NIST answer key (about 45 s)
python3 -m eval.baseline

# the AI investigator, on this machine's Claude Code login; scored the same way
python3 -m agent.run --name investigator

# score any run file with the same scorer
python3 -m eval.score --run runs/investigator/run.json

# re-check every certificate of the real run from the evidence file alone
python3 -m verifier.verify certs/*.json --facts evidence/case_facts.json

# tests (add `uv run` to include the DuckDB backend test)
python3 -m unittest discover -s tests -t .

# optional: rebuild the evidence file from the images (7.7 GB download, then 25 s)
scripts/fetch_data.sh --pc
uv run --extra extract python -I extractor/build.py data --out evidence/case_facts.json
```

`evidence/case_facts.json` is committed, so nothing above the last two lines needs the
images.

`--facts` takes a JSON evidence file or a DuckDB file with the schema in
[`extractor/schema.sql`](extractor/schema.sql).

## Repository layout

```
lean/
  ChainOfProof/Facts.lean      Kind, Fact, Slot            (contract with the extractor)
  ChainOfProof/Claim.lean      the brick IR
  ChainOfProof/Check.lean      lookup, precedes, holds     (the trusted checker)
  ChainOfProof/Sets.lean       approved sets
  ChainOfProof/Theorems.lean   properties of the checker
  ChainOfProof/Rules.md        rules, strengths, templates, timestamp conventions
  Miner.lean                   brute-force generators and mine_sound
checker/                       claim JSON → Lean certificate → kernel verdict; English templates
verifier/                      re-check certificates against the evidence
extractor/                     case images → evidence file (dissect); schema.sql; exhibits.json
evidence/case_facts.json       facts extracted from the real images (376 rows)
miner/                         every instance of the approved sets, no LLM
eval/reference.json            96 answer-key rows (the ground truth)
eval/labeled_claims.json       46 claims with a known answer
eval/score.py, baseline.py     the scorer and the reproducible baseline run
eval/results.json              last scored result, row by row
certs/                         certificates and proposal log of the baseline run
ui/public/run.json             the same run, bundled for the front end
fixtures/                      synthetic sample facts and certificate, for unit tests
tests/                         checker, verifier, scorer and miner tests
scripts/fetch_data.sh          download the case images
agent/                         the AI investigator: tools, MCP server, brief, runner
runs/investigator/             its scored run on the current evidence: certificates, proposal log, summary
```

## Sources

- Jagadeesan, Lubinski, Pitcher, Riely, Winebrinner. *Certificates for Verifiable Forensics*, IEEE CSF 2014. https://reed.cs.depaul.edu/cpitcher/research/2014-csf-certificates-for-verifiable-forensics.pdf
- NIST CFReDS Data Leakage Case. https://cfreds-archive.nist.gov/data_leakage_case/data-leakage-case.html
- NIST CFReDS Data Leakage Case answer key. https://cfreds-archive.nist.gov/data_leakage_case/leakage-answers.pdf
- Mulder (`mulder-dfir`), benchmark table and anti-hallucination design. https://pypi.org/project/mulder-dfir/
- Gladyshev. *Adding real time into state machine analysis of digital evidence*, 2006. https://researchrepository.ucd.ie/entities/publication/4263b040-0f09-4bc5-9cac-695bb31f366d
- AWS Open Source Blog. *Lean into verified software development* (Cedar). https://aws.amazon.com/blogs/opensource/lean-into-verified-software-development
