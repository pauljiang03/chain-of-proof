# Mulder comparison package: 60 questions

Status: **prepared, not finalized, not run**.
The user requested preparation only. Run the comparison only after finalization and a new instruction to execute it.

This package contains:

| File | Purpose |
|---|---|
| `MULDER.md` | Public instructions and all 60 question structures. |
| `questions.json` | The same public profile used by Chain of Proof. |
| `answers.template.json` | One unknown response for each question. It contains no expected values. |
| `manifest.json` | Input hashes, evidence segment hashes, and unfinished comparison settings. |

The seven evidence segments are not copied into this package.
Their hashes identify the image-container bytes, not the decompressed disk hashes.
No expected answers, old reports, API keys, or model outputs are included.
The separate [original 20-item package](../mulder-original20/README.md) preserves Mulder's published test.
This 60-question package is an expanded test, not a reproduction of that checklist.

## Finalization

Complete these items before execution:

1. Finish the readers, answer export, and proof review.
2. Independently review the reference and resolve its incomplete questions and list scopes.
3. Freeze the exact Mulder version and container digest or native environment.
4. Freeze our code revision and the common model, provider, limits, and three-trial protocol.
5. Use the same public acquisition information for both systems. Do not supply answer-key device mappings to one system alone.
6. Freeze the evidence, public profile, private reference, and scorer hashes.
7. Verify that the report can carry the requested JSON submission without a second investigator or prose judge.
8. Obtain the user's instruction to run.

The package does not claim that these items are complete.
The manifest leaves the model, budgets, version, and private reference hash unset.
Do not interpret its blank answer template as a measured result.

## Environment preparation

Mulder documents a native Linux installation and a Docker environment.
Its public `MULDER.md` mechanism supplies investigation context.
Use the [official usage guide](https://github.com/calebevans/mulder/blob/main/docs/usage-guide.md)
and [README](https://github.com/calebevans/mulder/blob/main/README.md) when the environment is selected.
No installation or model call has been performed for this package.

On the chosen host, create a dedicated evidence directory.
Copy only the seven listed image segments, `MULDER.md`, and `questions.json` into it.
Verify their hashes against the manifest.
Do not mount the repository or answer-key directory as investigator input.
Use a separate writable directory for each trial's logs and reports.

## Submission and scoring

Both systems receive the same public question structures and comparison rules.
The private expected answers remain outside their inputs.
The report must contain one complete schema-version-2 answer block.
A missing supported value must remain unknown.

After an authorized trial, extract that block without interpreting its prose:

```sh
.venv/bin/python -m eval.submission \
  --report /path/trial/report.md \
  --questions comparison/mulder/questions.json \
  --out /path/trial/answers.json
```

Use the frozen reference and scorer for both systems:

```sh
.venv/bin/python -m eval.benchmark \
  --reference /path/frozen-reference.json \
  --answers /path/trial/answers.json \
  --out /path/trial/results.json
```

These commands are instructions for later use. They have not been run on a Mulder trial.
If no typed block exists, extraction fails. It does not invoke an LLM judge.
Report all trials, their complete question counts, unresolved questions, limits, and resource use.
