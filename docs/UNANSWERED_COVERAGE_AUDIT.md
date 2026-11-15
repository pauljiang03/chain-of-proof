# Audit unanswered work without inventing answers

Priority: reject unsupported claims first, then increase supported answer coverage.
`agent.coverage_audit` compares public field declarations with saved authored and
retained binding counts. It reads no private reference, evidence file or model.
It emits no answer values and cannot establish that evidence exists or is absent.

Run it against a public question file, original binding document, saved projection,
its prepared projection plan, and an explicit catalog snapshot:

```sh
python -m agent.coverage_audit --public questions.json --document bindings.json \
  --projection projection.json --plan projection-plan.json --catalog catalog.json \
  --out coverage-audit.json
```

`--plan` can be omitted when the saved projection embeds its frozen `projection`
plan, as the experiment runner's projection artifacts do.

The plan digest must match the projection, and its public hash must match the
supplied questions. When a historical catalog digest is available, supply it with
`--projection-catalog-sha256`. Otherwise catalog lineage is explicitly unverified.
The binding document is hashed as a supplied artifact; its historical origin is
not authenticated by this tool. Preserve the run manifest and checkpoint receipts.
Canonical JSON hashes and exact file-byte hashes are recorded separately.

A changed public file or known changed catalog is refused by default.
`--allow-cross-revision` permits a clearly labeled declaration comparison, with
historical binding outcomes suppressed. This is a development comparison and
does not revise the old run or its score. Outputs are created exclusively.

Categories distinguish missing catalog support, invalid/missing public declarations,
declared unavailable scope, no authored bindings, recorded scope/meaning rejection,
other binding refusals, drops and output conflicts. They can coexist. Missing
catalog support does not distinguish a legitimate unsupported meaning from an
implementation gap: review the source and specification before changing a rule.
No binding does not mean no investigation. A retained value does not imply a
complete or correct answer. Malformed/foreign rows remain counted as unattributed.

Next development priorities identified from the published results and public gap
plan are Search Desktop tuples (answer owner), Search configuration/service groups
(answer owner), and Internet Explorer Search-index category/date-window observations
(third terminal, proposal pending). Literal registry exclusions can support partial
observations; they do not prove why an email is absent from a snapshot. Activity,
actor identity, causation and exhaustive inventories require their own premises.

For each proposed capability, test one known source sample through extraction,
the actual claim checker/replay and public projection, then substitute the wrong
object, timestamp role, date boundary or source scope and require refusal.
Key-informed examples are development tests; a new accuracy result requires a
separately identified run. Finite tests do not prove that false positives are impossible.
