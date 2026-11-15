# Final evaluation work

Base: `78ed3f0`. The saved Sol pilot is frozen. Do not change its inputs or scores.

The user authorized the five priorities below on 2026-11-14. All new trials need
new output directories and a recorded input/code manifest.

| Priority | Owner | Files and scope |
| --- | --- | --- |
| 1. Claim-linked answers | Root / `lean_gap_types` | New shared answer projection modules and tests. Root owns runner, API/MCP, report, CLI and evaluation integration. |
| 2. Coverage and large inventories | Other Codex terminal | `agent/brief.py`, SQL/plan helpers in `agent/tools.py`, a neutral coverage helper and tests. Agree on tool interfaces before integration. |
| 3. Larger verified counts | `optical_timestamps` | Census code in `checker/claims.py`, census emission in `checker/check.py`, Lean only if needed, and focused tests. Keep full source checks and kernel verification. |
| 4. Missing evidence support | Other Codex terminal | Source-grounded gap audit and small general reader fixes with tests. No answer-key edits. |
| 5. Reference and validation | Root / `journal_gaps` | Reference decision review, second-case readiness, integrated tests, and new bounded live validation when authentication is available. |
| Independent checker and UI | Claude, separate branch | Independent checker and CONAN-F rename merged from `97c435a`. Claude then moved to `finish/desktop-ui`; avoid that UI work. |

Root's worktree is `/private/tmp/cop-final-eval`, branch `finish/final-eval`.
The other Codex terminal uses a separate worktree and reports commits for integration.
Root integrates and pushes `main`. Agents do not merge or push `main`.

The first four implementation lanes are integrated. The second-case mechanical
smoke passed with 12 independently reverified certificates, reports and a portable
package. New comparison runtime preparation is in the other Codex terminal.
It must be frozen before the new model runs. The native Claude test needs approval
under the user's Sol-only instruction; automatic review blocked it before execution.
All 701 integrated regression tests and the Lean build passed at this checkpoint.

The shared projection must preserve a proposed claim's meaning. It must not fix
wrong values from the evidence, infer relevance from the answer key, or present
an unchecked proposal as certified. Keep supported partial fields. Record the
claim, field and source links for each output value. Question placement and answer
completeness are separate from proof validity.

Reports already exist in HTML, Markdown and JSON. Extend those outputs rather
than building a second report writer.

Reference review must preserve the published source and record any narrower
contract or correction explicitly. Source hashes prove byte identity, not the
truth of the answer key. Do not declare independent human review complete.

The first sandboxed login check could not access the local Claude login. A later
check outside the sandbox confirmed it is available. No API key was present in
this process. Do not send evidence to a different model destination without the
user's approval; credentials must not be copied into chat or Git.
