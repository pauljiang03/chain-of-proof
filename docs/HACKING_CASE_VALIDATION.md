# Hacking Case mechanical validation

The final checkpoint validates extraction, typed claims, proof replay, reports, and packaging on the official NIST CFReDS Hacking Case image. **It is not a model investigation or an answer-accuracy result.** No model was invoked by the smoke workflow, and no private answer key was used to select its claims.

The public contract contains all 31 questions. The script selects one available linked observation for each supported role, checks those observations, and checks a same-image digest comparison. It also deliberately tries to relabel an OS product observation as an email setting. That proposal must fail.

| Check | Final result |
|---|---|
| Extracted fact snapshot | 11,939 records; extraction completed with limitations |
| Typed observation roles exercised | 57 |
| Accepted claims | 58, including one image-digest comparison |
| Independent replay against the supplied fact store | 58 verified; 0 failed |
| `con-leche --verified` replay | 58 accepted; 0 failed |
| Deliberate wrong-role proposal | 1 refused |
| Added axioms in the 58 certificates | None; all recorded axiom lists are empty |
| Final verification package | Integrity passed; 58 verified; retained manifest hash matched |
| Public-contract readiness | 31 questions annotated; 3 unsupported stronger fields; 0 invalid fields |

These counts have different denominators. The 58 proof checks do not mean 58 correct answers, and they do not establish that all 31 questions can be answered. The single refusal is a negative control, not an estimated false-positive rate. Readiness checks available field meanings and observed record types; it does not check answer correctness or completeness.

## Retained limits

Three public fields need stronger evidence or an approved relation:

| Question | Meaning not yet supported |
|---|---|
| Q10 | Predominant account use across a stated population, metric, and interval |
| Q15 | The specific network interface used during the referenced setup |
| Q24 | A justified device/platform interpretation of captured traffic |

Account counters, a configured MAC address, and literal User-Agent text remain useful observations. They do not by themselves prove these stronger meanings.

Newsgroup subscription state is an additional extraction gap. The reader preserves retained DBX mailbox names, but it does not decode a reliable subscription flag. It reports this limitation in extraction health. A mailbox can remain after use or renaming; its presence does not establish current subscription.

The antivirus scan is partial. It reached the 300-second time limit, omitted one file, and recorded two scanner error entries: the timeout exit status and the time-limit explanation. The scan excludes deleted or unallocated data and other unstaged content. Its signature matches do not prove execution or malicious activity, and the partial scan cannot establish absence of malware.

Proof replay checks the declared conditions over the extracted records. It does not establish source authenticity, parser correctness, extraction completeness, or the relevance of a selected claim to a question. The HTML report is an output artifact; its presence is not an answer-quality test.

## Archive and source pins

The local archive is [runs/dev/hacking-mechanical-20261115T0355Z](../runs/dev/hacking-mechanical-20261115T0355Z/README.md). It preserves the final evidence snapshot, run, HTML and Markdown reports, smoke script, logs, public input receipts, and verification package. Earlier archives remain unchanged. The raw E01/E02 files remain in `data/hacking_case`; their download URLs and hashes are retained in the archive. Large run artifacts are local and ignored by Git.

The package was copied without changing its inventory. The later [package verification receipt](../runs/dev/hacking-mechanical-20261115T0355Z/receipts/package-verify.json) is stored outside the package directory. Historical temporary paths inside receipts remain unchanged.

| Stage | Recorded source revision |
|---|---|
| Extraction and typed-evidence feature | `6cff4fec112a078e10f542d211bad1468c5d3f85` |
| Workflow/scorer checkpoint | `08c7ce1d7225076fac3ec969fc4db2aa6318f9e7` |
| Package exporter and catalog fingerprint | `3da5c938e9e511e2ebf18298fbb6c800488557d6` |

These are coordinator-recorded stage pins, not a signed model-runtime identity. No model ran in this validation. The package correctly leaves its original-run code revision unknown and records the exporter revision separately in `toolchain.json`.

Retain these SHA-256 values outside the archive:

```text
facts.json
2955f5f061e8ab0664ad21bab30f2378acb73256f815613b0bbdc6e66c87ebc3

verification-package/manifest.json
9b06b6a09f3ad1cbb281bc7e5f6fc586d14fc6df6956043d78ff5d4574ded059

artifacts.sha256.json
313165c59553c19294a41ffa23fcb33e4a3cf8c1400ce33cd2411c14c7c9f74d
```

The outer inventory covers 159 files. It excludes itself to avoid a circular hash. A matching package hash detects changes relative to that retained checkpoint; it is not proof of the original disk's authenticity.

## Regression evidence

| Check | Result | Retained evidence |
|---|---|---|
| Full regression suite | 834 run; 833 passed; 1 skipped | [Log](../runs/dev/hacking-mechanical-20261115T0355Z/logs/regression-834.log) |
| Focused integration checks | 61 passed | [Log](../runs/dev/hacking-mechanical-20261115T0355Z/logs/focused-61.log) |
| Scorer follow-up | 40 passed | Coordinator-reported direct tool output; no saved log |
| Antivirus follow-up | 4 passed | Coordinator-reported direct tool output; no saved log |
| Package checks, including catalog fingerprint | 19 passed | [Log](../runs/dev/hacking-mechanical-20261115T0355Z/logs/package-tests-19.log) |

These overlapping checks are not additive. They are software regressions, not benchmark trials. Packaging did not rerun them or invoke a model.

## Replay the mechanical check

Use the declared Python dependencies and Lean toolchain. Run from the repository root. The following package replay performs no model call:

```sh
python -m verifier.package verify \
  --bundle runs/dev/hacking-mechanical-20261115T0355Z/verification-package \
  --expected-manifest-sha256 9b06b6a09f3ad1cbb281bc7e5f6fc586d14fc6df6956043d78ff5d4574ded059
```

To create a new deterministic proof exercise, choose an output directory that does not exist:

```sh
python runs/dev/hacking-mechanical-20261115T0355Z/scripts/workflow-smoke.py \
  "$PWD" \
  runs/dev/hacking-mechanical-20261115T0355Z/evidence/facts.json \
  /private/tmp/hacking-mechanical-replay-NEW
```

The script reads the repository's public question profile and current code. Use the recorded checkpoint when comparing a replay with this archive. Follow the separate [case instructions](HACKING_CASE.md) for an actual investigator run and subsequent deterministic answer scoring. Neither step has been performed by this smoke validation.
