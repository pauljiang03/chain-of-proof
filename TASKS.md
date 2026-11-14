# Work split

Four lanes that can run at the same time. Each lane has its own directory, so merges stay
clean. The lanes meet only at the four contracts below, and all four exist today, so
nobody has to wait for anyone else to start.

## Contracts (change only with everyone's agreement)

| Contract | Defined in | Who reads it |
|---|---|---|
| Fact row: `id, kind, t, res, obj, aux, prov` | `extractor/schema.sql`, `lean/ChainOfProof/Facts.lean`, `checker/facts.py` | everyone |
| Claim JSON: `{"usbMountedAs": [u, m]}`, `{"both": [...]}`, … | `checker/claims.py` (docstring lists all forms) | agents, miner |
| `check(claim_json, finding_id, source, question)` → result dict | `checker/check.py` | agents, miner |
| Certificate JSON and `proposals.jsonl` | `fixtures/sample_cert/N1.json` is a real example | UI, eval |

Adding a fact kind or a set touches three files in one commit: the Lean definition,
the Python mirror, and (for kinds) `schema.sql`. Say so in the team chat when you do it.

## Lane 1: Data (image → evidence DB)

**Goal:** `evidence.duckdb` holding real facts from the four NIST images.

- **Have:** schema, download script (`scripts/fetch_data.sh --pc`), sample fixture.
- **In progress (Paul):** first slice from the real images: USB devices, volume serials,
  LNK targets, file created/modified times.
- **Open, one file per artifact family under `extractor/`:**
  - browser history and search terms → `webSearch`
  - Recycle Bin `$I` records → `fileDeleted`
  - email (Outlook) → `emailSent`
  - CD burning traces → `cdBurn`
  - deterministic tags (authorized device list, confidential paths) → `tag`
- **Rules:** times in UTC microseconds (FAT stores local time: convert with the PC's
  zone); `res` per `lean/ChainOfProof/Rules.md`; every row carries `prov` with image,
  artifact path and tool.
- **Done when:** each kind has rows, and three rows per kind have been checked by hand
  against the NIST answer key.

## Lane 2: Lean and the miner

**Goal:** every instance of every set found and kernel-checked on the real DB.

- **Have:** brick IR, five sets, theorems, `Miner.lean` (two generators, `mine_sound`).
- **Open:**
  1. Batch checking: one Lean file with many brick theorems, returning a verdict per
     brick. 1,000 bricks check in 0.8 s, so check everything in the kernel.
  2. Candidate generation for all sets, either `lake exe mine` or a SQL join per set
     that feeds the batch checker. Generators are untrusted, so use whichever is faster
     to write.
  3. New sets as Lane 1 adds kinds (search then USB, email after copy, …).
  4. A closed-world brick for absence claims ("the only USB devices connected were
     these"), with the verifier confirming the cited list is every row of that kind.
- **Done when:** `mine` on the real DB writes bricks to `certs/`, all kernel-checked, with
  a count per set.

## Lane 3: Agents

**Goal:** an agent that answers case questions using only certified findings.

- **Have:** `check()` returns verified/rejected with the failing brick named; every
  call is logged to `certs/proposals.jsonl`.
- **Open:**
  1. Lead loop on deepagents with three tools: read-only `sql` over the evidence DB,
     `get_fact(id)`, and `check` (wrap `checker.check.check`).
  2. System prompt with the claim JSON forms and two worked examples from
     `tests/test_checker.py`.
  3. Challenger pass: for each narrative, try to certify the strongest alternative.
  4. Subagents per artifact family, only after one loop works end to end.
- **Start today** against `fixtures/sample_facts.json`; switch to the real DB when Lane 1
  lands it. Same `--facts` argument.
- **Done when:** one command takes a question and produces at least one certificate and
  at least one logged rejection on the real DB.

## Lane 4: UI, eval and demo

**Goal:** the two-minute demo and the numbers for the README.

- **Have:** certificate format, proposal log format, README benchmark table to fill.
- **Open:**
  1. Viewer over `certs/*.json` and `certs/proposals.jsonl`: timeline of findings,
     certificate drawer (sentence, cited artifacts with provenance, rules, strength,
     trust tier), rejection feed.
  2. `eval/answer_key.json`: the 20 answer-key items Mulder scores, and a scorer that
     reports coverage, contradicted findings and rejection rate.
  3. Demo script, video, Devpost text.
- **Start today** against `fixtures/sample_cert/N1.json`.
- **Done when:** the viewer shows a real run, and `python -m eval.score` prints the table.

## Checkpoints

| When | What must work |
|---|---|
| Sat noon | Real evidence DB with USB, volume, LNK and file-time facts; one real certificate |
| Sat 6 PM | Miner output on the real DB; agent loop producing certificates; viewer on real certs |
| Sat midnight | Full run, eval table filled, rejection demo scripted |
| Sun 5 AM | Feature freeze. Video and Devpost only |
| Sun 8 AM | Submitted |

## Before you push

```bash
cd lean && lake build && cd ..
python3 -m unittest discover -s tests -t .
```
