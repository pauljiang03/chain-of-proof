# Sol with/without-checker pilot

This is a small, explicitly bounded development pilot. It is separate from the
unfinished full A/B/C/D protocol in `comparison/abcd/` and changes no production
checker, reference, or answer adapter.

The first completed Sol 6.1 pair is documented in
[the 2026-11-15 pilot result](PILOT_SOL61_20261115.md).

Two fresh GPT-6.1 Sol subagents receive the same public case, extracted facts,
question contract, read tools, and wall-time cap. A records every submitted claim
and returns only an unverified receipt. C receives the existing Lean checker's
verdict and diagnostics. Both produce one literal, typed answer block. Neither
agent may read the private reference, prior reports, repository code, or the other
agent's work. These are procedural restrictions, not an operating-system sandbox.

After both agents stop, B replays A's exact sealed candidate stream in order.
It preserves duplicates and whole conjunctions, performs no repairs or model
calls, and independently verifies accepted certificates.

Both live arms use the same structural transport contract: claims are JSON
objects, questions are strings, and optional revision IDs are strings. Non-object
claim payloads are transport errors in both arms and are retained in the bridge
log separately from candidate counts. Unsupported forms and malformed contents
inside an object reach A unchanged; A performs no semantic validation.

The reported measurements are deliberately separate:

- **A/C answer agreement:** unchanged literal model JSON scored with the same
  deterministic reference. Both answer blocks are unverified. C's checked claims
  do not certify that every answer value follows from them.
- **A/B claim filtering:** accepted, refused, malformed, unsupported, and failed
  original proposals. A refusal is not automatically a ground-truth error.
- **C proof results:** checker attempt history and independently replayed
  certificates, separate from answer correctness.

There is no B answer-accuracy score in the original frozen pilot. The new shared
claim-field projector is available for future trials with explicit model-authored
bindings. It does not add bindings or new scores to the saved pilot.
Unresolved reference questions remain visible and unscored. Missing
or malformed final answer blocks produce an unavailable measurement; they are
not repaired or converted into invented abstentions. A single pair supplies no
statistical significance or universal false-positive result.

## Freeze and execution

The coordinator uses `comparison.ablation.pilot` to freeze input/code hashes,
the requested `gpt-6.1-sol` model override, fresh-context policy, A/C/B order, and
equal wall-time caps before launching either agent. The initial pilot uses one
15-minute cap per live arm. Token totals, costs, provider model revision, and
unexposed platform traces remain unknown; no matched-token or immutable-model
claim is made. Both arms share the existing extraction snapshot, and this pilot
does not measure end-to-end extraction speed.

The coordinator initializes A and C with the runtime module, then launches each
investigator with `fork_turns=none` and `model=gpt-6.1-sol`. The persistent
`runtime session` command loads the facts once and provides newline-delimited
JSON calls for `forms`, `sql`, `fact`, and `check`. It exposes no scorer or file
inspection command. Closing the session releases its exclusive run lock.
Finalization occurs only after the investigator and bridge have stopped.

The final model-authored summary is preserved without rewriting. Evaluation uses
`answers.evaluate_trial` with independently retained summary, public-question,
and private-reference hashes. The private reference enters only this separate
post-investigation step. All trial failures and timeouts are retained.

Runtime and replay are experimental tools in the repository checkout. Use
`python -m comparison.ablation.runtime --help` for their command contract.
