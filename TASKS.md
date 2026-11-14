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

- **Real data is here:** [`ui/public/run.json`](ui/public/run.json): 100 findings and
  16 rejections from the real case images. Regenerate with `python3 -m eval.baseline`.
- **Small file for layout work:** [`ui/public/run.sample.json`](ui/public/run.sample.json)
  (7 findings, 4 rejections, synthetic).
- Good ones to design around: `M024` (heuristic chain across a reformatted USB stick,
  six parts), `M005` (strong chain, authorized device), `P01` (rejection).

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

Done: extractor for USB devices, volumes, shortcuts, jump lists, searches and file
times; miner; scorer; first real `run.json`.

Next, in the order the scorer says matters (rows of the answer key each would add):

1. Files copied to RM#2, recovered from FAT directory entries after the format (17).
2. Recycle Bin records (14). 3. E-mail from the Outlook OST (12). 4. CD burns (5).
5. Agent loop with `sql`, `get_fact`, `check`; challenger pass. Scored by `eval.score`.
6. A closed-world brick for absence claims.
- **Done when:** `python3 -m eval.baseline` shows every question above zero and an
  agent run beats the miner's row count.

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

The numbers and the story. The scorer and a 96-row reference exist (`eval/`); run
`python3 -m eval.baseline` to see them.

1. **Audit the reference.** Spot-check `eval/reference.json` against the
   [NIST answer key](https://cfreds-archive.nist.gov/data_leakage_case/leakage-answers.pdf)
   (each row has its page). It was transcribed by hand; a second pair of eyes makes the
   numbers defensible.
2. **Mulder mapping.** Mark which reference rows correspond to the 20 items Mulder
   scores (https://pypi.org/project/mulder-dfir/), so we can print a row comparable to
   theirs. Add any of the 20 we lack.
3. **Scoreboard** panel in the UI from `eval/results.json`: the per-question table, the
   gate result (16/16 false claims refused), and Mulder's published rows beside ours.
4. **Demo.** Two-minute script, backup recording, video, Devpost text. Opening line and
   the rejection moment first; the reformatted-USB finding (`M024`) is the story.
- **Done when:** the scoreboard renders from `results.json`, and a full demo has been
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
