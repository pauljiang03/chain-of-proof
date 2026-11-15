# Workstreams and terminal handoff

Updated: 2026-11-15 UTC. Read before assigning work.
The project is CONAN-F. The desktop app is Conan. The `cop` command and
`ChainOfProof` Lean library retain their names for compatibility.

## Ownership

**Both cases have finished live runs, exact replay and fixed scoring.**
The answer terminal ran fresh Sol 6.1 A/C investigators from the frozen, clean
`cf97b96` runtime, with 900 seconds per live arm. A separate reference role scored
all six submissions. The [new results](comparison/ablation/RESULTS_SOL61_TWO_CASE_20261115.md)
show low coverage and retained errors. The approved frontend is integrated at
`bffaac2`, with app tests and browser checks complete.
Later documentation and frontend work do not change the frozen runtime.

| Owner | Current state |
|---|---|
| Root Codex | Owns integration, combined tests, complete fresh evidence, readiness, archives and pushes. Active worktree: `/private/tmp/cop-system-evidence-coverage`. Combined suite and later UI tests passed. |
| Answer terminal (`01a1dc3d`) | Completed the two case lanes, replay and operational audit. Now audits public source-to-answer mappings and implements prospective coverage fixes in isolation. No further model calls are planned. |
| Third terminal (`01a1dd77`) | Completed the owner-approved frontend patch, focused tests and browser checks. Root integrated the reviewed commit at `bffaac2`. |
| Root helper: formal types and events | Formal checks, qualified claim sentences, selected full Hacking proofs and public compatibility recheck complete. No private evaluator was read during the recheck. |
| Root helper: host fields and review | Host fields and independent checker review complete. Reviewed the newer desktop changes and fixed unsupported summary claims. Native provider calls remain untested. |
| Root helper: structured sources | Completed source-tested partition, configuration and Search fields. Sealed the implementation and experiment archives; all copied files and input bindings passed readback checks. |
| Independent reference reviewer | Completed all six fixed scores with 69 input bindings checked and a separate mismatch diagnosis. Preserves the scores and private expected values; reviews prospective contract policy separately. |

The current four-window split gives root soundness review, central roles/Lean,
reference alignment and integration. The answer terminal owns prospective
Q2/Q46/Q50/Q42 mappings and timestamp display. The third terminal owns the public
coverage audit and a generic Q44 date-window proposal. The fourth terminal
(`01a1de6a`) owns independent source-to-answer tests and selected real-source
checks. Shared requirement files have one owner until handoff. Reject unsupported
claims first, then increase answer coverage. Key-informed tests are development.

The public coverage audit is integrated at `9029890`; its 32 targeted checks and
CLI runs on both saved C submissions passed. It reports input lineage and binding
outcomes without answer values or evidence-presence inference. All 34 Data Leakage
and 20 Hacking unanswered C questions have no authored bindings in those saved
submissions. That does not establish that the agent did no investigation.

Independent tests at `1e54651` exercise synthetic known cloud-log bytes through
the production reader, Lean/replay, public answers and reports. Six controls cover
mixed containers, foreign snapshots, timestamp meanings and altered provenance.
Root ran the integrated audit and source-to-report suites together: 18 tests
passed. This is bounded validation, not a new benchmark score or a zero-FP proof.

The standalone Search timestamp helper at `1fdbced` passes ten interval tests.
It uses exact 100ns values and explicit half-open bounds, rejecting unsupported
roles and ambiguous local-day boundaries. It is not wired into answer admission.
Q44 still needs actual-source IE classification and an explicit public date-window
policy; see [the proposal](docs/SEARCH_TIME_WINDOW_PROPOSAL.md).

The prospective answer batch at `cbdd4bc` restores narrow Q2/Q46/Q50 mappings
with source-role, row and origin checks. It adds an explicit timestamp-display
capability for reviewed time roles and closes conversion of ISO-shaped product
text. Its implementation owner ran 416 integration tests and nine strict-draft
checks; root's combined new-feature suites passed 56 tests. The prospective draft
now has 65 supported and 293 unsupported leaf occurrences. This is capability
coverage, not measured answer accuracy. Hacking's actual profile and all frozen
matching rules stay unchanged. Q42 service-only support and Q44 interval admission
are the next isolated work; both need their declared meanings and source limits.

The later integrated batch at `58293c1` adds Q42's selected-service configuration
label and Q44's explicitly narrowed indexed-store/date-window draft. The public
draft is version 3, with 69 supported and 289 unsupported leaves. Q44's revised
instruction defines the indexed observation and interval; it does not establish
equivalence with the original usage question. Hacking representation changes
remain a review-only proposal with unresolved reference and precision policies.

Independent review found that the current-control-set selector accepted integer
values with the wrong registry type. Root now requires a unique native DWORD
selector and an existing control set. An initial exact-Python-type check rejected
Dissect's legitimate uint32 subclass; the corrective commit accepts integer
subclasses while rejecting booleans and retaining the native-type requirement.
Actual SYSTEM readback passed after that correction, and wrong-type cases were
refused. Root's 96 combined checks and eight updated Q42 tests passed. These
overlap other reported suites; do not add their counts as unique tests.

The selected actual-source Q2/Q46/Q50 probe passed three Lean/replay certificates,
ten native answer fields and eight refusal controls. Receipt SHA256:
`f75326f6e77d34fa65e9ab65c2dceac14353e08438bbc4eade1713e6ba619c70`.
The native IE marker, literal URL and 100ns timestamp were read back for one ESE
row; that is separate from the extracted 47/46 row inventory. Database state 2,
unreplayed logs and no new whole-image hash remain explicit limits.

The final corrected-reader Q42/Q44 source probe passed: two actual Lean/replay
certificates, four native answer fields, nine refusal controls and HTML/Markdown
report checks. The fresh SYSTEM reader retained Q50's exclusion value. Receipt
SHA256 `768ad8e2db10184b93ff6e2a17fccca74cf1a5c337b6a24f00d45dba7a938e60`.
Root verified the four shared runtime-file hashes and exact runner bytes against
the sample receipt. The reusable runner is integrated at `6c2e90a`.

Three intermediate audit assertions are retained: requested/native registry-key
casing, projected leaf order, and an unavailable field selected for a negative
control. They required runner corrections, not product fixes or extra model
attempts. Fresh corrected SYSTEM facts were retained and reused. None of these
checks changes the frozen experiment scores. The source-development supplement
is sealed at `runs/dev/post-ablation-answer-development-20261115T1149Z/`, manifest
SHA256 `1aee4206d2d371a0741fc2a716e88893aed3bdcf88accff3d4dd323530aed926`.
All 330 files, 45 declared bindings and three prior-archive references passed
readback. Earlier seals remain unchanged.

The next authorized step is a small fresh development investigation after
readiness. Root owns integration, archives and final reference alignment. The
answer terminal owns the Hacking fixes and sole model dispatch. The third window
owns independent contract/precision review and trial-freeze preparation. The
fourth owns negative controls and post-run replay/projection/report checks.
The exact timestamp scorer currently loses sub-microsecond precision; a synthetic
zero-tolerance counterexample confirms this. Its prospective fix and version
review are required before the next run. Old scorers, submissions and scores stay
frozen. No fresh model investigation has started.

The precision fixes are now integrated. Native ShutdownTime preserves seven
fractional digits and requires one REG_BINARY value. One actual Hacking source
claim passed Lean/replay, exact projection and diagnostic UTC display; seven
misleading alternatives were refused. Scorer 2.2 uses exact rational timestamps
and tolerances, so distinct 100ns values no longer match under zero tolerance.
Independent checks include 802 scorer assertions and 107 FILETIME roundtrips.
Root's overlapping precision/host/UI suites passed 73 tests; builder/publisher
checks passed 29. The focused Hacking public builder retains explicit reference,
source and launch holds. Fresh complete snapshots for both cases are complete,
with reader hashes checked before and after and matched to the integrated code.
Data Leakage has 409,971 records, no failed reader and 17 limitations; Hacking has
14,468 records, no failed reader and 18 limitations. Their facts hashes are
`259f97ebe98f1648783c1aa8498dc0050539296e794cf91e9584535f8f48268a` and
`ff6dc61a61c9c0062e0571e9808e640293afc797f594460c77020c209fcad969`.
The complete app suite passed 144 tests with one platform skip after the local
socket/process tests ran outside the restricted sandbox. The initial sandboxed
attempt could not exercise those tests; it is not a product regression.

The C-only freeze mode and focused reader/report fingerprints are integrated.
Root's focused and legacy freeze checks passed 13 tests. Actual prepared Hacking
public fields Q2/Q3/Q4/Q8 passed four Lean/replay claims, exact projection and
reports, with six refusal controls. Reference alignment and actual per-case
freeze validation remain required. The approved next trial is one fresh C run
per case, 300 seconds each, at most two parallel investigators. It is a focused
development test, not a full comparison or a causal test of Lean feedback.

Remote UI commits `6e40997` and `03261a2` are merged. The short prose lead remains;
it now counts recorded identifiers, retains case-distinct computer names and
states source-timestamp ranges without inferring physical devices or activity
boundaries. Existing examiner edits in the original main checkout remain intact.

The source-support and soundness repair batches passed their recorded checks.
The complete experiment inputs passed readiness and remained fixed during runs.
Use isolated worktrees for new work. Reassign completed workers to independent
review or a remaining implementation task, rather than leave them idle. Root
serializes commits in the shared source worktree to prevent index conflicts.
Do not edit another terminal's files without agreeing on ownership. Do not control
Terminal or Claude with computer-use tools. No direct Claude acknowledgement is
known; do not claim one.

## Latest validation

The source/runtime tree at `445ef58` passed 1,638 tests: 1,636 passed and two
were skipped. The native PFF test passed separately in the source-reader
environment; the other skip applies only to other operating systems. The later
UI merge at `8bf03a0` passed 127 app tests with one platform skip. No core source
changed. All 95 source hashes from the ten-case audit still match. The public
assembler check passed. Earlier suites and the repaired stale-wording failure
remain in the archive.

Real-source tuple checks passed Lean and independent replay, with selected
ConLeche checks and mixed-subject controls. Full extraction exposed a native
filename subtype problem that the fixture tests missed. The narrow reader fix
preserves the strict value emitter. Fresh snapshots at `1ae4082` contain 409,971
Data Leakage records and 14,468 Hacking records, with no failed reader and 17/18
explicit limitations. Both were rebuilt at `57c1c5f` after the UDF repair with the
same counts. Original attempts remain diagnostic artifacts, not final inputs.

The [latest implementation](docs/SYSTEM_EVIDENCE_COVERAGE.md) adds 94 roles and
signed source values, for 199 roles and 243 fact kinds. The local archive is
`runs/dev/system-evidence-20261115T0805Z/`; its final manifest records the validation
chain. Previous sealed archives remain unchanged. Implementation checks are not
accuracy scores.

The later literal-value fixes passed 142 app-related tests with one platform skip
and three browser surface checks. The original invariant harness passes 17/18:
one legacy positive fixture now lacks required file identity. A separately adapted
valid fixture passes 18/18. A new supplement preserves both results and the fixes.
These finite checks do not prove every reader or composition correct.

The reviewed integration includes UI changes through `27ba010`. The main checkout
also retains another terminal's original five UI edits. The third terminal
integrated their approved changes separately. Do not reset, stash or overwrite
those original files. The experiment uses a separate, clean frozen checkout.

The frontend follow-up at `bffaac2` restores evidence cards and short-report
timeline counts. It preserves literal labels and property values, including case,
spaces and line breaks. The app suite passed 143 tests with one skip. The final
label-only change passed 22 focused checks and three browser surface checks.
The adapted invariant harness passed 18/18 before that final display change.
Root checked all nine merged file hashes against the validation receipt; all
match. No core source changed from the frozen runtime. Frontend receipt SHA256:
`d5fbe474fa823cbfdc332b083218b8f98ebcf596909d47857afbe5e212cc4393`.

## Readiness and dispatch

Both strict public derivatives remain held. Current schema compatibility is
55 supported / 303 unsupported Data Leakage leaf occurrences and 14 / 24 Hacking
leaves. Repeated alternatives count separately. These are not question-accuracy
percentages. The [public gap plan](eval/PUBLIC_IMPLEMENTATION_GAPS.md) separates
completed work, candidate capabilities and unresolved meanings/source selections.

The user's matched Sol 6.1 experiment passed readiness and is now scored.
The answer terminal owned dispatch to avoid duplicate runs. Its coordinator
and notes are outside the repo:
`/private/tmp/cop-v3-experiment-coordinator.py` and
`/private/tmp/cop-v3-experiment-dispatch.md`. The recorded parallel-case schedule
retains A then C within each case and at most two live investigators. Shared-host
timing is a limitation of this comparison.

A compatible scoring derivative must be frozen before investigation. Original
expected values, match rules, question denominators and measured submissions must
not be silently changed. The independent reference review is separate from
builders and investigators. It is not an LLM judge of experiment answers.

The prepared local bundle is `/private/tmp/cop-legacy-agreement-release-20261115/`.
It supports an explicitly labeled development comparison under original matching
rules. It does not assert semantic equivalence. All 60/31 questions and original
46/31 scorable statuses remain; Data Leakage's other 14 questions remain visible.
Hacking Q28/Q29 original-population bindings are unsupported. Normalization is off.
The compatible development bundle passed the actual freeze validator. Hacking's
first attempt exposed a packaging error: its private envelope lacked
`public_contract_revision`. A new derivative adds only that field. All 31 question
records and every other byte remain unchanged. The independent reference role
verified this, then ran exact freeze and `validate_frozen`. The original bundle,
failed preflight, readiness record and sealed archives remain unchanged.

For every future case, run the actual freeze validator and `validate_frozen`
before issuing readiness. A preparation script's own metadata check is not enough.
Builders receive only the public reattestation; private answers stay with the
reference and scoring roles.

After readiness passes, create complete fresh snapshots and freeze the code,
public contract, compatible private reference, facts, model and budget. A and C
use the same inputs/tools/time limit. B replays A exactly without another model
call. Checkpoint-prefix projection must not include later candidates. Scoring
starts only after both investigators stop. Do not replace the requested accuracy
comparison with an unscored smoke run.

## Latest measured state

[Latest two-case comparison](comparison/ablation/RESULTS_SOL61_TWO_CASE_20261115.md),
frozen at `cf97b96`: Data Leakage A/B each have four complete, six partial and
36 unanswered questions; C has five complete, seven partial and 34 unanswered.
Fourteen reference questions remain unevaluable. A/B match 18/1,627 scorable
fields; C matches 75/1,627. Every arm retains 14 extra fields and 13 unequal values.
Zero wholly incorrect questions does not imply zero incorrect assertions.

Hacking has eight complete, 20 unanswered and three incorrect questions in each
arm, with 10/52 matched fields. Q2/Q4/Q8 remain incorrect under the frozen matcher.
All 113 Data Leakage C and 11 Hacking C certificates passed independent replay.
B verified 45 Data Leakage candidates and 11 Hacking candidates. One unbound
malformed Hacking candidate did not affect answers. Proof checks and answer
agreement remain separate measurements.

Data Leakage's first launch failed at transport and remains retained. Attempt 2 A
reached the deadline without a final response; scoring used its saved checkpoint.
Its last logged tool finished normally. The cause of the subsequent wait is
unknown. All four checkpoints were in budget, with zero calls after deadlines.
The controller records A's 39.190-second cleanup delay and shared-host timing.

Run source: `/private/tmp/cop-matched-ablation-20261115T0918Z/`.
Public scoring receipt SHA256:
`30f6f8165d0205c963950dec92ad675425a4e815e71c58396f5069affe41c1ba`.
Both actual frozen snapshots and all 69 scored input bindings passed validation.
Original run archives and failed attempts remain unchanged. The two Mulder
packages and the planned D arm remain unrun. Native-provider orchestration still
needs its own validation.

The experiment archive is `runs/dev/matched-ablation-20261115T1019Z/`, with manifest
SHA256 `36849d2cd24bfaf3a7540c53bfab81f15b5cb959338388eee26a67d6ba60d8dc`.
It preserves 564 files and verified external input bindings. Private evaluator
payloads, full private scores and raw internal model traces are excluded.

## Trust boundary

Lean proves the declared formal statement relative to extracted records and rules.
Python readers, source authenticity, source completeness and public meaning
choices remain trust boundaries. No universal zero-false-positive claim is justified.
Unsupported meanings and unavailable evidence stay explicit. Never manufacture
missing answer bindings or use a private key to steer an investigator.

The interface plans remain in [BACKEND_HANDOFF.md](BACKEND_HANDOFF.md),
[APP_HANDOFF.md](APP_HANDOFF.md) and [FEATURE_HANDOFF.md](FEATURE_HANDOFF.md).
The measured-run details remain in [FINAL_EVAL_HANDOFF.md](FINAL_EVAL_HANDOFF.md).
