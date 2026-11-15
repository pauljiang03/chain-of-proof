# Final evaluation handoff

Updated: 2026-11-15 UTC. The five requested priorities have implementation and validation results below. Native provider validation and full reference review remain incomplete.

| Priority | Delivered | Remaining limit |
|---|---|---|
| 1. Claim-linked answers | Shared A/B/C projection, answer tool, source ledger, report fields and independent verification before scoring | Question relevance and complete answers are not proved |
| 2. Coverage and large inventories | Saved pages, separate finding/note limits, missing-field review within the original budget | Predicate exhaustion does not prove a complete question answer |
| 3. Larger verified counts | Census limit 2,048; unchanged Lean rules; 518/747 total and distinct proofs also passed con-leche | Large distinct counts can reach the time limit |
| 4. Evidence support | General registry omissions fixed; mail-body and document-metadata gaps diagnosed from source | Those additional reader/semantic fields remain future work |
| 5. Reference and validation | All 14 reference issues reviewed; separate Q53 derivative; fresh evidence; mechanical and live second-case checks; frozen NIST A/B/C comparison | Original 14 stay unresolved; Mulder unrun; native Claude test blocked |

The final combined code includes Claude's desktop/report work, reviewed citation and stale-preview fixes, and common-field `anyOf` export support. Final regression suite: 763 tests run, 762 passed, one platform test skipped. No Lean source changed after the passing build.

The measured comparison is frozen at clean `c2b9753`, before the UI and schema fixes. Do not change its outputs, add bindings, reproject its answers or revise its scores. A/B fully answered 8/46 questions; C fully answered 7/46. All 63 B and 96 C certificates independently verified. This single pair did not show an accuracy gain or a semantic-predicate refusal. See [the result](comparison/ablation/RESULTS_SOL61_20261115.md).

Local archives:

- `runs/dev/sol61-nist-v2-20261115T0217Z/`: latest scored comparison, all outputs, exact replay, audits and hashes.
- `runs/dev/sol61-smoke-20261115T0209Z/`: second-case live operational smoke; no accuracy key.
- `runs/dev/case2-workflow-20261115T015403Z/`: mechanical product workflow, reports and portable package.

The frozen runtime remains `/private/tmp/cop-sol61-smoke-runtime`. The implementation worktree is `/private/tmp/cop-final-eval`. Do not confuse their commits.

The schema fix accepts only explicit common paths and compatible types across every `anyOf` branch. It retains missing and conflicting fields; it does not infer relevance, choose a branch, repair a claim, or certify arbitrary metadata. It has no new accuracy result.

The local Claude login is available. Automatic approval review rejected the native test because selected forensic records would be sent to Claude.ai despite the user's Sol-only instruction. That call did not execute. Do not retry it through another route without destination approval. No credentials belong in chat or Git.

Reports already exist in HTML, Markdown and JSON. Extend the shared writer. Coordinate with the other terminal before changing shared files, preserve all saved runs, and inspect main before the next merge.
