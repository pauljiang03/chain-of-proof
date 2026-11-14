# Work split

One person runs the pipeline; three build what the judges see. The two sides meet at
one file, `run.json`, and a sample of it exists today, so nobody waits for anyone.

| Lane | Owner | Directory |
|---|---|---|
| 1. Pipeline: data, Lean, miner, agents, export | @pauljiang03 | `extractor/`, `lean/`, `checker/`, `agent/` |
| 2. Front end: evidence graph and timeline | @Taygeta-gl | `ui/` |
| 3. Front end: app shell, certificate view, rejection feed | @skj04 | `ui/` |
| 4. Eval and demo: answer key, scorer, video, Devpost | @michellejiang2017 | `eval/`, `ui/` (scoreboard) |

The split is by lane, not by known skills: swap if someone else is the better fit.

## Why the front end matters

- "Visualization and demo" is one of Arlequin Track 1's four criteria. Their own
  example ideas include "a visualization that links people, devices and events".
- Amazon scores user experience at 25%.
- Each judge gives us two minutes. Most will not know what a proof assistant is. They
  need to *see* a claim get rejected and *see* a finding trace down to a disk artifact.

## The contract: `run.json`

The front end is a static site that reads one JSON file. No backend to build or host.

- **Build against today:** [`ui/public/run.sample.json`](ui/public/run.sample.json)
  (7 findings, 4 rejections, synthetic facts, real kernel verdicts).
- **Real data arrives as:** `ui/public/run.json`, same shape, written by
  `python -m checker.export --certs certs --out ui/public/run.json`.

```
run.json
├── case         { name, generated_at }
├── stats        { proposals, verified, rejected, by_strength, by_rule }
├── findings[]   verified certificates
│   ├── finding_id, question
│   ├── english             the sentence to show; never reword it
│   ├── parts[]             { part, english, rules, strength }: one sentence per brick set
│   ├── cited_facts[]       { id, kind, t, res, obj_text, aux_text, row_sha256, prov }
│   │                       t is UTC microseconds; prov has image, artifact, tool
│   ├── rules[]             R1…R5, T: see lean/ChainOfProof/Rules.md
│   ├── strength            "strong" | "heuristic" | "judgment"
│   ├── trust_tier, axioms  "kernel" and [] for everything so far
│   └── lean                the Lean source of the certificate, for a "show proof" panel
└── rejections[] proposals Lean refused
    ├── finding_id, question, claim, reason
    └── parts[]             { part, ok, bricks[] }: bricks are "ok …" / "FAIL …" lines
```

Two rules for anything shown on screen:

1. **Never generate or paraphrase finding text.** Show `english` as is. The claim that
   the sentence is exactly what Lean checked depends on it.
2. **Show the weak links.** Strength and rules are part of the finding, not a tooltip.

## Lane 1: Pipeline — @pauljiang03

- Real images → `evidence.duckdb` (USB devices, volume serials, LNK targets, file
  times first; then browser, Recycle Bin, email, CD burning, tags).
- Miner: every instance of every set, kernel-checked in batches.
- Agent loop with `sql`, `get_fact`, `check`; challenger pass.
- New sets and a closed-world brick for absence claims.
- `run.json` from a real run, refreshed as the pipeline grows.
- **Done when:** `run.json` holds real certificates that answer answer-key questions.

## Lane 2: Evidence graph and timeline — @Taygeta-gl

The main picture: how the evidence links up.

1. **Graph.** Nodes are entities (devices, volumes, files, searches) and events
   (cited facts). Edges are the bricks that join them. Build it from each finding's
   `cited_facts` and `parts`: two facts sharing an `obj_text` or `aux_text` are linked.
   React Flow or similar.
2. **Timeline.** Cited facts on a time axis by `t`, grouped by kind, colored by the
   strength of the finding that cites them. Clicking a fact highlights its findings.
3. Clicking anything opens Lane 3's certificate view for that finding.
- **Done when:** on the sample file, a judge can follow USB device → volume → opened
  file → tag in one picture, and see the order of events.

## Lane 3: App shell, certificate view, rejection feed — @skj04

The frame everything sits in, and the two views that make the trust argument.

1. **Shell.** Vite + React (or whatever you are fastest in), loads `run.json`, falls
   back to `run.sample.json`. Header with the `stats` counters. Layout slots for the
   graph, timeline and scoreboard. Deployable as a static site.
2. **Certificate view.** For one finding: the sentence; one row per part with its own
   sentence, rules and strength; the cited artifacts with image, artifact path and
   hash; a strength badge; "checked by the Lean kernel, no axioms"; a collapsible
   panel with the Lean source.
3. **Rejection feed.** Each refused proposal: the question, what was claimed, and the
   brick that failed, in red. This is the demo's key moment, so make it legible from
   two meters away.
- **Done when:** the sample file renders end to end, and swapping in a new `run.json`
  needs no code change.

## Lane 4: Eval and demo — @michellejiang2017

The numbers and the story.

1. **Answer key.** `eval/answer_key.json`: the 20 items Mulder scores on this case
   (its scorecards are public: https://pypi.org/project/mulder-dfir/), each with the
   NIST answer and which fact kinds it needs. Source:
   https://cfreds-archive.nist.gov/data_leakage_case/leakage-answers.pdf
2. **Scorer.** `python -m eval.score ui/public/run.json`: items covered by a certified
   finding, findings the key contradicts, share of proposals rejected. Same three
   definitions as Mulder so the columns compare.
3. **Scoreboard** panel in the UI: our row next to Mulder's published rows.
4. **Demo.** Two-minute script, backup recording, video, Devpost text. Opening line and
   the rejection moment first; everything else is optional.
- **Done when:** the scorer prints the README's results table, and a full demo has been
  rehearsed twice with a timer.

## Checkpoints

| When | What must work |
|---|---|
| Sat noon | Real evidence DB; first real `run.json`; UI shell renders the sample file |
| Sat 6 PM | Graph, timeline, certificate view and rejection feed on real data; answer key done |
| Sat midnight | Full run, scorer output in the UI, demo rehearsed once |
| Sun 5 AM | Feature freeze. Video and Devpost only |
| Sun 8 AM | Submitted |

## Before you push

```bash
cd lean && lake build && cd ..                  # only if you touched lean/ or checker/
python3 -m unittest discover -s tests -t .
```
