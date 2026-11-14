# Parallel feature handoff

2026-11-14. F4–F7 implementation is complete. C0 owns final integration and push
from the shared checkout; this terminal used isolated worktrees and did not change
saved runs, private references, or extraction output. No live provider run was made.

## Commits to integrate

| Lane | Original commit(s) | Files |
| --- | --- | --- |
| F4 portable package | `bc34333`, `730e68d`, `358c662` | `verifier/package.py`, `tests/test_verification_package.py` |
| F5 coverage | `9a1afd6` | `agent/coverage.py`, `tests/test_coverage.py` |
| F6 history | `f328833a` | `agent/history.py`, `tests/test_claim_history.py` |
| F7 export | `3bfb1ec`, `fc1e9ec` | `checker/export.py`, `tests/test_export_metadata.py` |

Some commits already have different cherry-pick IDs on C0's branch. Integrate
each change once. Our `finish/evidence-features` branch also merges C0's committed
`af4d96a` checkpoint, including the explicit-revision integration.

## Interfaces and behavior

- `bundle(..., case_metadata=None, facts_metadata=None, public_questions=None,
  answers=None, health=None, audit_expected_head=None)` preserves certificate
  data and adds separately qualified audit, coverage, history, and run-manifest
  metadata. Case metadata is applied before coverage calculation. Answers are
  supplied explicitly; arbitrary JSON siblings are never read.
- Audit summaries bind the exact snapshot bytes to the verified chain. Missing,
  empty-valid, and invalid logs remain distinct. Non-finite audit JSON values
  cannot leak into exported history. Legacy certificate directories need a
  verified proposal entry or a same-ID Lean file for discovery.
- `summarize_coverage` separates extracted, explicitly inspected, cited, and
  certified counts. SQL aggregates do not count as record inspection. Missing
  public answers, logs, and health data remain unmeasured. Invalid audit data
  cannot establish inspection coverage.
- `validate_revision` and `summarize_history` use explicit same-run links and
  actual event order. Similar claims do not imply a correction. Duplicates are
  attempts, not new proofs; revisions remain outside certified claim fields.
- `build_package(run, facts, out)` exports to a new directory after verification.
  `verify_package(bundle, expected_manifest_sha256=None)` verifies inventory,
  hashes, actual audit, regenerated proofs, stored Lean, and report consistency.
  It rechecks every payload and directory inventory after proof verification.

```sh
python -m verifier.package build --run RUN_JSON --facts FACTS --out NEW_DIRECTORY
python -m verifier.package verify --bundle DIRECTORY
```

The complete supplied fact store is copied, including for census proofs. A fixed
allowlist prevents copying keys, credentials, or arbitrary siblings. Original
facts/questions receipts are checked when present. Declared prompt, case-profile,
health, and other omitted inputs are explicitly `not_packaged`; recorded paths
are never followed. Missing investigator/model provenance is unknown.

Verification covers the supplied records and artifacts, not original-disk
authenticity or extractor correctness. Coverage/history remain recorded summaries.
External manifest/audit checkpoints are needed to detect complete replacement.
Report regeneration requires a compatible renderer; bundled code is never run.

## Validation

- Combined optional-API regression checkpoint: **441 tests passed** in 74.9s,
  with C0's `af4d96a` changes and initial F4 package commit.
- Final input-binding, strict-JSON, and package-race changes: **31 focused
  exporter/package tests passed** in 14.4s. Package tests use real Lean,
  census claims, tampering, path/symlink rejection, and mutation during proof
  verification; they do not call a model provider.
- `lake build`: passed, 11 jobs.
- Independent cross-reviews found the audit non-finite-value and package mutation
  gaps; both have regression tests and are fixed in the final commits above.

C0 still owns the final combined runner/report checkpoint and final regression
run. Preserve the existing distinction between diagnostic proof gaps and certified
findings, and keep receipt-only experimental mode free of proof-gap feedback.
