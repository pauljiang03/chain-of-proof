# Hacking public representation proposal — review only

This directory contains a public-only review proposal, not an answer contract,
generated derivative, release, experiment input, or scoring authorization.
`proposal.json` deliberately uses a proposal schema rather than the runnable
policy schema accepted by `eval.representation_derivative.prepare`.

The proposal binds the exact frozen public ancestor bytes by SHA256. It changes
the proposed endpoint label, case ID, contract revision, and timestamp display
instruction. The original frozen contract and measured outputs remain unchanged.
No private reference, expected answer payload, or scoring result was consulted.

The concrete changes are:

- Q2 `/operating_system`: preserve the exact recorded ProductName value under
  the existing public case/whitespace comparison. Do not strip vendors, rewrite
  product names, or introduce OS aliases. This is a recorded configuration field,
  rather than a claim that the configured OS was successfully used.
- Q4 `/time_zone_setting`: propose explicit `zone-label-offset-v1` comparison
  with `label_mode: casefold_whitespace`. Both the retained label and signed
  numeric UTC offset matter; no standard/daylight label substitution, timezone
  label inference, or historical transition claim is authorized. This formatting
  equivalence does not establish an IANA timezone or historical machine setting.
- Q3 `/installed_at` and Q8 `/shutdown_at`: retain the native source timestamp,
  exact UTC instant, and every fractional digit. Propose an explicitly declared
  UTC report display using `x-claim-display`, preserving source/display metadata
  in the frozen projection. UTC is a neutral presentation convention, independent
  of Q4. The existing local-display instruction must be replaced, not silently
  left in force alongside UTC.

The replacement instruction includes this exact clarification:

> Report display timezone is an explicit presentation convention; it does not establish the machine historical local timezone. Native source timestamp retained.

Q8 precision matching remains **review required**. The proposal defaults to
exact-instant comparison without tolerance or truncation; representation must
preserve native fractional precision, including 100ns digits. No reviewed
permission exists to drop a fractional part, round it, compare only whole
seconds, or apply a nonzero tolerance. The source reader's already discarded
precision cannot be reconstructed from formatted text. A future activation must
review raw source precision, exact matching implementation, and independent
reference alignment before making any comparison claim.

Implementation references are `agent/answer_representation.py` (pure exact report
display), `agent/answer_projection.py` (explicit reviewed temporal capabilities
and opt-in display annotation), `eval/representation_derivative.py` (public-only
representation preparation), and `eval/match_normalization.py` (zone label/offset
comparison). The current derivative builder does not by itself implement all
proposed instruction and display-policy changes; this proposal is not its input.

Independent reference alignment is unresolved for every affected field. That
review belongs to the separate reviewer and may not alter the frozen ancestor,
historical measured submissions, original endpoint, or old results. Neither the
new endpoint nor exact timestamp comparison is activated here. No runnable
`questions.json`, aligned contract, model run, score, or accuracy conclusion is
produced by these two files.
