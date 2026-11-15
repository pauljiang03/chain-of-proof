# Why three Lean-feedback answers were incorrect

The frozen C run has three wholly incorrect answers under its declared reference contract. The exact certificates behind them were checked again against the frozen facts: all three passed. These are answer interpretation and scope failures, not evidence of an unsound Lean proof.

The relevant single-record forms are narrow. `programRan`, `journalPathAt` and `fileRemovedAt` check the cited extracted record's kind. Their certificates and fixed sentences retain source limitations. The answer projector previously checked the selected value, JSON shape and primitive type, but had no declared requirement for what the destination answer field meant.

| Question | Exact supporting claim | What the answer did | What remains unproved |
|---|---|---|---|
| Q18: email application | A031: `programRan [1393]` | Put the recorded executable `OUTLOOK.EXE` into the application field | Source-supported product/version identity and a link to email communication. The strict reference names a product/version; the executable is relevant evidence, not a fabricated value. |
| Q34: files copied to CD | A087: 17 `journalPathAt` observations, starting at record 329931 | Put `[unresolved ancestor]` suffixes into the requested path list | Historical ancestor resolution, the requested copy/staging relationship and a complete inventory. The cited provenance explicitly disclaims copy/disc-write proof. |
| Q52: anti-forensic actions | A082: `programRan [1444]` plus `fileRemovedAt` records 62432, 62433, 62434 and 62436 | Used recorded kinds/times/targets as the requested action list | The requested action categories, relationships and wider sequence. A retained removal flag is not exact action onset; an execution or removal record does not prove wiping or purpose. |

Q18 has 0 matched / 1 missing / 1 mismatched reference field. Q34 has 0 / 20 / 17. Q52 has 0 / 83 / 15. These are contract-agreement counts, not numbers of fabricated facts. The reference was not changed. The earlier `anyOf` export bug did not cause these three wrong answers.

`answered` in the transport means a value was supplied. It is not a claim that the whole question is answered. Missing required fields must remain visible without erasing valid partial observations.

## Implemented boundary check

A public answer schema can now attach `x-claim-requirement` to an exact answer value. It declares accepted semantic roles and can restrict the exact form/field pair. For example, a field asking for an installed product name can permit:

```json
{
  "type": "string",
  "x-claim-requirement": {
    "semantic_types": ["program"],
    "selectors": [{"form": "programInstalledAt", "field": "program"}],
    "meaning": "Name recorded in an installation record; this alone does not establish use.",
    "evidence_needed": "A source-supported installation observation with the recorded product name."
  }
}
```

The selector matters: `programRan.program` and `programInstalledAt.program` currently share the `program` role. A role name alone cannot distinguish them. Matching an installation role still does not establish email use or a version that was never recorded.

The shared projector applies the same compatibility check to A, B and C. It uses the immutable claim-field catalog, not expected answers, prose interpretation or source-value repair. Timestamp formatting cannot turn an observation time into an action time. Every reachable `anyOf` requirement must hold. Invalid requirements and attempts to bypass a parent annotation fail closed.

An incompatible binding stays in the diagnostic ledger with the offered role, required role and stated evidence need. It is omitted from the answer field. Valid sibling fields remain. The certificate and narrow observation are unchanged. Whole-candidate filtering in B still cannot change values or reveal frozen conflicts.

`answer(question_id)` now previews the requirements and compatible catalog fields, including requirements inside schema-valued additional properties. Catalog support is not a claim that the needed evidence exists. Roles absent from the catalog report `no_catalog_support` before binding.

This is a deterministic check against a declared public contract, **not a new Lean theorem about question meaning**. The contract itself needs review. Unannotated contracts retain their existing behavior and unverified question placement. No universal zero-false-positive claim follows.

## Separate public diagnostic profile

[The three-question profile](../eval/contracts/answer_meaning_debug_v1/questions.json) declares the stronger meanings explicitly and gives the narrow observations separate fields. Its case ID is distinct. It has no private answer key and no accuracy score. The current catalog cannot establish all of the stronger roles; it will report those gaps rather than invent support.

For Q18, the profile explicitly requires a product/version identity linked to communication. That is a stronger public declaration than the original short question, whose strict score required a product/version name. Do not present the profile as the unchanged benchmark.

The original 60-question files, all frozen model outputs and all scores remain unchanged.
The later [three-question diagnostic](../comparison/ablation/RESULTS_MEANING_DIAGNOSTIC_20261115.md)
retained 21 verified claims and narrow observations. It submitted no incompatible
bindings, so it did not demonstrate the guard catching a live error. It had no
accuracy score. The [latest correctness fixes](CORRECTNESS_FIXES.md) make explicit
field requirements the product default and add durable checkpoints; they do not
supply missing evidence or certify a complete English answer.

## Evidence and verification

New read-only diagnosis archive: `runs/dev/lean-answer-debug-20261115T0256Z/`.
It contains the exact binding-to-claim-to-source traces and `reverification.json` with the certificate hashes and three successful checks. Archive manifest SHA-256:
`c166717a2f7ebfcb07d03a392ef2c77d753fc09e596314e01f08cf6afa03a3f0`.

The original comparison remains at `runs/dev/sol61-nist-v2-20261115T0217Z/` and is summarized in [the measured results](../comparison/ablation/RESULTS_SOL61_20261115.md).

Regression tests use a separate synthetic case. They show that the narrow claims pass real Lean and independent replay, that the legacy unannotated export can reproduce all three scope errors, and that declared requirements block those bindings while preserving supported observations. Tests also cover shared role names, timestamp formatting, malformed contracts, alternatives, partial fields, product-tool/report integration and unchanged A/B filtering.

Final validation: 775 tests run, 774 passed and one platform test skipped. The Lean build passed all 11 jobs. No new AI trial was run.

## Remaining work

- Add reviewed source fields and relations for product identity/version and actual use. Do not infer these from an executable basename alone.
- Recover historical path ancestry and copy/staging links with identity and time constraints. Do not reconstruct missing paths from the reference.
- Represent the requested action relationships and distinguish observations from purpose, causation and wiping conclusions.
- Improve inventory completion. The separate coverage trace shows C fetched later Q44 records but did not claim or export them. SQL pagination and inspected-but-unbound rows are not fully tracked by the current inventory planner. This is separate from proof validity and the three incorrect answers.
