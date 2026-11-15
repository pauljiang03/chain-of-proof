# Source claims and answer boundaries

This change fixes unsupported promotion at two boundaries: the sentence attached to a proof, and the use of a claim value as an answer. It also retains answers during an investigation. No new model experiment or accuracy score is included.

## What changed

| Boundary | Current behavior |
|---|---|
| Shortcut target | The certificate describes retained target and volume metadata. It does not assert a file opening. |
| Message record | The certificate describes retained message metadata and its timestamp. It does not assert transport or delivery. |
| Software registration | The certificate preserves the source and timestamp meaning. A key last-write time is not called the installation time. |
| USB record | The certificate describes the source record and exact serial/volume links. It does not turn a USBSTOR key timestamp into connection onset. |
| Answer field | The product requires an explicit public claim-role requirement. An absent or incompatible requirement cannot receive a verified answer value. |
| Partial answer update | Supported fields can persist while unsupported proposals remain diagnostics. An invalid replacement or conflicting update preserves the prior answer. |
| Final answer output | The new `claim-bindings-v3` protocol saves investigator-authored checkpoints during the allowed time. A timeout can retain the last valid checkpoint. |

The source predicates and identity joins remain checked by Lean. Their sentences now describe exactly the source observations. Timestamp ordering and census sentences use the same narrower wording. The UI reports rule types without treating a missing label as certainty.

Strict projection is the product default. The low-level projection API retains an explicit legacy-compatible default for old protocols. Both A and C use the same public preview and strict field policy in v3. The preview does not give A Lean feedback. A checkpoint binds its session, time, document hash and candidate-log prefix; later claims cannot supply an earlier saved answer. No coordinator invents bindings after timeout.

Declared-role compatibility is still not a Lean proof of a complete English answer. A contract can be wrong or incomplete, an investigator can choose irrelevant evidence, and a parser can misread its source. These fixes do not establish universal zero false positives or an accuracy advantage on every run.

A subsequent public-contract review found another gap: individually compatible fields can refer to different subjects or events. For example, an image name and two hashes can come from three images; a search query and its time can come from different history records. A candidate containing several independent claims does not establish a relationship between them. Explicit row relationships and source-scope checks are still being implemented. Generic application observations also require a source-sensitive rule before they can answer execution questions. New model experiments remain on hold for this work.

## Better evidence and explicit gaps

The new `application_identity` reader follows live Windows App Paths registrations. It reads bounded PE version resources without executing the files. It retains literal product names, descriptions and versions, along with registry locations, byte offsets, language tables and complete file hashes. It does not infer a marketing year, authenticity, execution or use for email.

A deterministic read of the Data Leakage PC produced 285 records from 21 hashed binaries and 88 literal metadata values, with no extraction issues. Five selected source claims passed independent replay with no axioms. A deliberate wrong-role proposal was refused. These are mechanical checks, not answered test questions.

The journal reader now refuses an ambiguous directory rename between `OLD_NAME` and `NEW_NAME`. Both historical-path export routes apply the same restriction. Without validated raw journal bytes, it retains raw names and diagnostics. It also refuses missing scope, reused references and invalid intervals. Shortcut-derived volume records preserve their originating image, exhibit, timestamp meaning and uncertainty.

On the real PC journal, the path recovery counts stayed unchanged. The review found 752 missing ancestor identities. New diagnostics identify the exact scoped ancestor, the last resolved chain, the valid byte interval, the blocking condition and the historical evidence needed. A present-day MFT path does not silently supply a missing historical prefix.

## Scope of the next evaluation

The original 60-question contract, reference, model outputs and scores remain unchanged. That contract lacks claim-role annotations. V3 rejects it before starting an investigator instead of silently returning empty answers. A separate public meaning review and derivative contract are required before a new strict 60-question trial.

The Hacking Case has 31 annotated public questions. Its three stronger unsupported fields remain explicit. Its model pilot was prepared but never launched. New model experiments remain on hold until the correctness work and public contracts are ready.

Older certificates retain their original sentence text. Replay them with their recorded checker version. The current checker can reject an older sentence that differs from the corrected template. This is not a rewrite or rescore of a historical trial.

## Validation

The combined regression suite ran 913 tests: 912 passed and one platform test was skipped. Lean built all 11 jobs. The first combined run found one stale expected sentence in a census test; the assertion was corrected to the narrower mapping-record wording, and the full suite passed again.

The local archive is `runs/dev/correctness-fixes-20261115T0424Z/`. It retains the source-only intake, five-certificate proof exercise, deliberate wrong-role refusal, journal validation, scripts and test logs. It contains no new model result or accuracy score. Large local artifacts are not stored in Git.

The archive inventories 30 files. Its manifest SHA-256 is `c5c737aba9f6e8176b66d219df16e2abcec1bb3738a78a903a2c5da7cf5d62ca`.

Source commits: reader and formal corrections `1e64486`, answer policy and checkpoints `9a297f3`, combined code `c7427ed`, and the assertion correction `658722f`. See [the terminal handoff](../WORKSTREAMS.md) for current ownership and [the original diagnosis](INCORRECT_ANSWER_DEBUG.md) for the three incorrect answers.
