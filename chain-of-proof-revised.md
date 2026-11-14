# Chain of Proof

**Machine-checked digital forensics: Lean 4 brute-forces the evidence, LLM subagents hunt for what matters, and proofs snap together like bricks.**

> "Every sentence in our report is a theorem."

HackPrinceton Fall '26 project spec, v3.1: v3 added subagents, the brick IR and brute-force search in Lean; v3.1 corrects the Lean sketch and several claims against the compiled code (§19). Submissions are due **Sun Nov 15, 8:00 AM** (hard deadline). Judging runs 9:30 AM – 2:30 PM.

---

## 1. One-liner

An AI forensic investigator that never puts an unverified claim in front of the investigator.

- A **brute-force miner written in Lean** enumerates every instance of every known forensic pattern in the extracted evidence.
- A team of **LLM subagents** hunts for patterns the miner doesn't know yet and assembles the findings that answer the case.
- Every finding is built from small, typed **bricks** in a Lean 4 intermediate representation (IR), checked against facts extracted by deterministic forensic tools.
- Checked bricks go into a shared **brick library** and snap together into bigger theorems, up to full narratives such as "confidential file → unauthorized USB → deleted → 'successfully secured' email."
- The investigator gets a proof graph: raw artifacts at the bottom, narratives at the top, and every link machine-checked.

## 2. Tracks

| Track | Why we fit |
|---|---|
| **Main: Business & Enterprise** | The track description explicitly lists cybersecurity and privacy |
| **Arlequin AI – Track 1: AI-Driven Forensics** | Built for their criteria (see §12) |
| Amazon – Best Practical AI Innovation | Multi-step planning, parallel agents, adapts to verifier feedback |
| LangChain – Best use of deepagents | Lead agent + subagents on deepagents (subagents are built in) |
| ChatOverflow leaderboard | Free entry: connect our coding agent |

## 3. Problem

- **Investigators can't trust LLM output.** Incident response findings feed legal proceedings, regulatory responses and executive decisions. One fabricated timeline entry or wrong attribution can leave a backdoor in place or send people after the wrong suspect. (Source: BlueTeamCon 2026 talk on AI in IR.)
- **Existing LLM forensics tools check that a citation exists, not that it supports the sentence.** GenDFIR (RAG plus LLM timeline analysis) writes narratives. Mulder, an open-source agent, goes further: every finding must cite a real tool call, and an adversarial phase challenges each finding. On the same NIST case we use, its best published configuration (Claude Opus 4.6) scores 45% full match and 95% detection, with 10% of claims contradicted by the answer key. That false-positive column is our target.
- **Case backlogs keep growing.** Investigators need speed *and* rigor.

## 4. Core idea

```
Lean miner + subagents (search)  ──propose──►  Brick claims (Lean IR)  ──checked by──►  Lean (trusted)
                                                     │
                                     verified bricks ─► Brick library ─► snap into bigger claims ─► narratives
```

Four design choices:
1. **Lean 4 as the IR between search and verification.** Search is broad and fuzzy; checking is exact. The certificate sits in between: claim, cited facts, rules used and proof.
2. **Brute-force search runs in Lean itself.** Lean is a compiled programming language. The miner tries every combination of facts for every known pattern, keeps the ones that pass the same `holds` checker, and a one-line theorem proves that anything it emits is correct.
3. **The IR is built from bricks.** A tiny set of primitive checks, plus named compositions of them (sets), plus a lemma (`holds_both`) that snaps proven pieces together.
4. **Subagents run in parallel safely because Lean gates what they produce.** Workers can only add to the shared library through the Lean check, so one worker's mistake can't spread to the others.

### Prior art we build on
- **Certificates for Verifiable Forensics** (Jagadeesan, Pitcher, Riely et al., DePaul, IEEE CSF 2014). Proposes *forensic certificates* as intermediate artifacts between search and verification. They formalized a Honeynet case in Coq by hand. **We automate both the search and the certificate writing.**
- **Gladyshev & Patel, finite-state-machine event reconstruction** (2004–2006). Includes computing time bounds for events whose time is unknown. This is our stretch feature (§10).
- **AWS Cedar.** Lean used as an executable spec/IR, with production code differentially tested against the Lean model.
- **Agent architecture research.** In Google Research/DeepMind/MIT's study of 180 agent configurations ("Towards a Science of Scaling Agent Systems", 2026):
  - centralized coordination works best;
  - independent agents with no checking amplified errors up to 17.2×;
  - coordination helps most on parallelizable tasks.

  Anthropic's Oct 2026 guidance says to keep one main loop and use subagents for parallel work in fresh context windows. Forensics fits: the artifact families can be searched in parallel, and Lean is the checker.

## 5. Architecture

```
┌────────────┐  [1] Extractor (deterministic)          ┌──────────────────────────────┐
│ Disk image │──► TSK / plaso / parsers ─► UTC ─► ids ─►│ Evidence DB (DuckDB)         │
└────────────┘     + deterministic tags                 │ facts + entities + provenance│
                   (authorized serials, path patterns)  └──────────────┬───────────────┘
                                                                       │ facts.jsonl / codegen / REPL (§7.1)
            ┌──────────────────────────────┬───────────────────────────┤
            ▼                              ▼                           ▼
 [2] Lean brute-force miner    [3] Lead investigator agent ── spawns ──► subagents (parallel)
 compiled `lake exe mine`:     plans questions, reads library index     • artifact specialists
 every set × every fact combo  composes narratives                      • set designer
 + chainer (bricks × bricks)                                            • challengers (adversarial)
            │                              │                            │
            └──────────────┬───────────────┴────────────────────────────┘
                           ▼  candidate bricks
            ┌──────────────────────────────────────────┐
            │ [4] Lean gate                            │  bulk: `mine_sound` (🟧)
            │     kernel `decide` per certificate (🟩) │  core Lean 4, no Mathlib
            └──────────────┬───────────────────────────┘
                           ▼  only checked bricks
            ┌──────────────────────────────────────────┐
            │ [5] Brick library (blackboard)           │  dedup by canonical claim hash
            │ level · color · studs · certificate      │
            └──────────────┬───────────────────────────┘
                           ▼
            ┌──────────────────────────────────────────┐
            │ [6] Report: proof graph + timeline       │  English rendered by templates, not LLM
            └──────────────────────────────────────────┘
```

### Trust boundary
| Component | Trusted? | Why |
|---|---|---|
| Extractor + deterministic tags | Yes | Community-validated tools, re-runnable; tags are plain code over facts |
| Primitive checks (`is`, `val`, `link`, `before`) + `holds` | Yes | About 40 lines of Lean, reviewed once |
| Lean kernel | Yes | Small trusted kernel; 🟩 bricks rely on it alone |
| Lean compiler (to run `mine`) | Yes, but labeled | Bulk-mined bricks rely on it, the same trust as `native_decide`, so they're 🟧 until kernel-promoted |
| Fact verifier script | Yes | Re-checks cited facts against DB rows (and image bytes, stretch) |
| Candidate generators inside `mine` | **No (and that's fine)** | Generate-and-test: only `holds` decides. A generator bug can cause misses, never false bricks (`mine_sound`) |
| Set *definitions* (named compositions) | **Can't break soundness** | They only combine primitive checks, so a bad set can be rejected or meaningless but never "proves" something false about the facts |
| Set *interpretations* (English template + strength label) | Human-approved | This is where meaning lives, so a human signs off |
| LLM lead agent + subagents | **No** | Can be wrong; can't get a claim into the library that its cited facts don't support |

## 6. The brick IR (Lean 4 sketch)

> §6.1–6.5 match `lean/ChainOfProof/`, which compiles on Lean 4.35.0 and is the source of truth. Use **core Lean only, no Mathlib** (`Lean.Data.Json` and `Std.HashMap` ship with core).

### 6.1 Atoms: facts (generated by the extractor, never by an LLM)
```lean
inductive Kind where
  | usbInsert | volumeMount | lnkTarget
  | fileCreated | fileModified | fileDeleted
  | webSearch | emailSent | cdBurn
  | tag              -- obj = tagged entity, aux = tag id (deterministic or labeled judgment)
  deriving DecidableEq, Repr

structure Fact where
  id   : Nat   -- row id in evidence DB
  kind : Kind
  t    : Nat   -- UTC microseconds
  res  : Nat   -- timestamp uncertainty in µs: the true time is within (t - res, t + res)
               -- (NTFS = 1, exFAT and FAT created = 10_000, FAT modified = 2_000_000)
  obj  : Nat   -- interned primary entity (path / device serial / query / user)
  aux  : Nat   -- interned secondary entity (volume serial, recipient, …)
  deriving Repr

-- For the miner's JSON input, in the miner module only (so certificates don't import it):
--   deriving instance Lean.FromJson, Lean.ToJson for Kind
--   deriving instance Lean.FromJson, Lean.ToJson for Fact
```
A tag fact's `t` is the time the tag was assigned, never 0. Otherwise `before tag event` would certify that a label "happened" before a real event.

### 6.2 Studs and the four primitive bricks
A **stud** is a connection point on a fact: one of its entity slots (`obj`/`aux`) or its time.
Every claim is built from four primitives:

```lean
inductive Slot where | obj | aux
  deriving DecidableEq, Repr

def Fact.get (f : Fact) : Slot → Nat
  | .obj => f.obj
  | .aux => f.aux

inductive Claim where
  | is     (f : Nat) (k : Kind)                        -- brick: fact f has kind k
  | val    (f : Nat) (s : Slot) (v : Nat)              -- stud equals a constant (e.g. a tag id)
  | link   (a : Nat) (sa : Slot) (b : Nat) (sb : Slot) -- connector: same entity in two studs
  | before (a b : Nat)                                 -- connector: a happened before b (beyond resolution)
  | both   (c d : Claim)                               -- snap two claims together
  deriving Repr

def lookup (fs : List Fact) (i : Nat) : Option Fact :=
  fs.find? (fun f => Nat.beq f.id i)

-- x certainly happened before y: the gap exceeds BOTH timestamp uncertainties.
def precedes (x y : Fact) : Bool :=
  Nat.blt (x.t + x.res + y.res) y.t

def with1 (fs : List Fact) (a : Nat) (k : Fact → Bool) : Bool :=
  match lookup fs a with
  | none => false
  | some x => k x

def with2 (fs : List Fact) (a b : Nat) (k : Fact → Fact → Bool) : Bool :=
  with1 fs a fun x => with1 fs b fun y => k x y

-- Structurally recursive so `decide` can evaluate it in the kernel.
def holds (fs : List Fact) : Claim → Bool
  | .is f k => with1 fs f fun x => x.kind == k
  | .val f s v => with1 fs f fun x => Nat.beq (x.get s) v
  | .link a sa b sb => with2 fs a b fun x y => Nat.beq (x.get sa) (y.get sb)
  | .before a b => with2 fs a b precedes
  | .both c d => holds fs c && holds fs d

-- The snapping lemma: two proven bricks give a proven bigger brick.
theorem holds_both {fs : List Fact} {c d : Claim}
    (h₁ : holds fs c = true) (h₂ : holds fs d = true) :
    holds fs (.both c d) = true := by
  show (holds fs c && holds fs d) = true
  rw [h₁, h₂]
  rfl
```
Why it is written this way: `decide (a < b)`, `max`, `==` on `Nat`, and a two-discriminant `match … | _, _ => …` each pull the `propext` axiom into `holds`, and it then shows up in `#print axioms` for every certificate. With `Nat.beq` / `Nat.blt` and single-discriminant matches, certificates depend on no axioms. `holds_both` avoids `simp` for the same reason, so snapped narratives stay axiom-free too.

### 6.3 Sets: named compositions (= forensic rules)
Each set is a Lean `def` built from primitives. It comes with:
- an **English template**,
- a **strength label**,
- a **candidate generator** in the Lean miner (§7.2) that enumerates its instances.

```lean
namespace Sets
-- R1+R2 (strong): USB insert `u` and volume mapping `m` share a device serial
def usbMountedAs (u m : Nat) : Claim :=
  .both (.is u .usbInsert) (.both (.is m .volumeMount) (.link u .obj m .obj))

-- R3 (strong): LNK `l` targets a file on the volume recorded by mapping `m`
def openedFromMount (l m : Nat) : Claim :=
  .both (.is l .lnkTarget) (.both (.is m .volumeMount) (.link l .aux m .aux))

-- R4 (heuristic): on one volume, created after last-modified ⇒ copied to this location
def copiedHere (c m : Nat) : Claim :=
  .both (.is c .fileCreated)
    (.both (.is m .fileModified)
      (.both (.link c .obj m .obj) (.both (.link c .aux m .aux) (.before m c))))

-- R5 (strong): deletion record `d` is later than event `x`
def deletedAfter (d x : Nat) : Claim :=
  .both (.is d .fileDeleted) (.before x d)

-- Tag check: entity in slot `s` of fact `f` carries tag `tagId`, via tag fact `g`
def tagged (f : Nat) (s : Slot) (g tagId : Nat) : Claim :=
  .both (.is g .tag) (.both (.val g .aux tagId) (.link g .obj f s))
end Sets
```

| Set | English template | Strength | Miner generator (joins on) |
|---|---|---|---|
| `usbMountedAs u m` | "USB {serial} was connected and mounted as volume {vol}" | Strong | usbInsert × volumeMount, same `obj` |
| `openedFromMount l m` | "{path} was opened from volume {vol}" | Strong | lnkTarget × volumeMount, same `aux` |
| `copiedHere c m` | "{path} was likely copied here (created after last modified)" | **Heuristic** | fileCreated × fileModified, same `obj` and `aux` |
| `deletedAfter d x` | "{path} was deleted after {event}" | Strong | `$I` record × event, ordered |
| `tagged f s g T` | "{entity} is {tag}" | Depends on the tag's source | tag facts × any fact, same entity |

### 6.4 Brick colors (trust tiers)
Each brick gets a color, and **a composite takes the weakest color of its parts.**

| Color | Meaning |
|---|---|
| 🟩 **Kernel** | Strong sets + deterministic tags, proven by `decide +kernel` (`#print axioms` reports "does not depend on any axioms") |
| 🟨 **Heuristic** | Uses a heuristic set (e.g. R4 copy signature) |
| 🟦 **Judgment** | Relies on an LLM-labeled tag (e.g. "this search query is about data leakage"). Shown as a stated assumption, never as proof |
| 🟧 **Compiled / closed-world** | Bulk-mined and not yet kernel-promoted, uses `native_decide`, or is an absence claim ("no other USB connected in window") |

Detecting the tier: on Lean 4.35 a `native_decide` proof lists an axiom named `<theorem>._native.native_decide.ax_…`, not `Lean.ofReduceBool`. So don't match on a name. Treat an empty axiom list as 🟩, anything beyond `propext` / `Quot.sound` / `Classical.choice` as 🟧, and `sorryAx` as a failed proof (Lean still adds the theorem after an error).

A color mixes two separate things: how a brick was checked (kernel or compiled) and how strong its rules are (strong, heuristic, judgment). The certificate JSON keeps them as two fields, `trust_tier` and `strength`, and the UI derives the color.

### 6.5 Snapping bricks into a narrative
```lean
open Sets

-- caseFacts: generated per narrative = union of its bricks' cited facts
theorem B1 : holds caseFacts (usbMountedAs 4512 4513) = true := by decide +kernel
theorem B2 : holds caseFacts (openedFromMount 4600 4513) = true := by decide +kernel
theorem B3 : holds caseFacts (tagged 4600 .obj 9001 T_CONFIDENTIAL) = true := by decide +kernel
theorem B4 : holds caseFacts (tagged 4512 .obj 9002 T_UNAUTHORIZED) = true := by decide +kernel
theorem B5 : holds caseFacts (.before 3100 4512) = true := by decide +kernel

-- Level 3 narrative: a confidential file was opened from an unauthorized USB,
-- and that USB was connected after search 3100
def N1 : Claim :=
  .both (usbMountedAs 4512 4513)
    (.both (openedFromMount 4600 4513)
      (.both (tagged 4600 .obj 9001 T_CONFIDENTIAL)
        (.both (tagged 4512 .obj 9002 T_UNAUTHORIZED) (.before 3100 4512))))

theorem N1_holds : holds caseFacts N1 = true :=
  holds_both B1 (holds_both B2 (holds_both B3 (holds_both B4 B5)))
```
- `caseFacts` here is generated **per narrative**: the union of its bricks' cited facts, a few dozen. All its bricks are stated over the same list, so they snap together directly with `holds_both`. (`holds_mono` is proved in `Theorems.lean`: a brick proven on its own small list holds on any list that resolves the same ids to the same facts.)
- Proof terms *are* the assembly instructions. The proof graph in the UI is drawn straight from them.
- Tags such as `T_UNAUTHORIZED` are computed by the extractor: the device serial isn't in the case brief's authorized list (RM#1). `T_CONFIDENTIAL` comes from a deterministic path rule. Both are 🟩. A tag like "leakage-related query" comes from an LLM label and is 🟦.

## 7. Connecting the data to Lean, and brute-force search

The goal is to prove a lot automatically, then **surface the few theorems that matter**.

### 7.1 How data gets into Lean (three bridges)

Lean never touches the disk image. It only sees numbers: the extractor turns every artifact into a `Fact` row and every string into an interned id.

```
disk image ─► extractor (Python) ─► DuckDB
                                     ├─ facts     (id, kind, t, res, obj, aux, row_sha256, provenance…)
                                     └─ entities  (id ↔ string: paths, serials, queries, users)
                                          │
  (A) bulk:  export facts.jsonl ─────────►│ compiled Lean `lake exe mine` reads it (IO + Lean.Json),
                                          │ brute-forces every set, writes bricks.jsonl
  (B) proof: codegen certificate files ──►│ Python writes Bricks/Batch_017.lean with cited facts as
                                          │ Lean literals + `theorem … := by decide +kernel`
  (C) live:  agent `check()` ────────────►│ same codegen, sent to a warm Lean REPL (Kimina Lean Server /
                                          │ LeanInteract) with ChainOfProof preloaded → pass/fail + error
```

**(A) One line of `facts.jsonl`.** Lean reads only the six IR fields; provenance stays in DuckDB.
```json
{"id":4512,"kind":"usbInsert","t":1427119200000000,"res":1,"obj":101,"aux":0}
```
`entities` row 101 holds the device serial string. The English renderer looks strings up there; Lean never needs them.

**(B) A generated certificate file:**
```lean
import ChainOfProof
open ChainOfProof Sets

namespace Batch017
def f4512 : Fact := ⟨4512, .usbInsert,   1427119200000000, 1, 101, 0⟩
def f4513 : Fact := ⟨4513, .volumeMount, 1427119201000000, 1, 101, 88⟩

-- brick id = canonical hash of (set, args)
theorem b_9f3a : holds [f4512, f4513] (usbMountedAs 4512 4513) = true := by decide +kernel
end Batch017
```

**(C) Live checks** use the same codegen, but the source goes to a warm REPL process instead of a file, so agents get pass/fail plus the Lean error in about a second.

Measured: a cold `lake env lean` on one certificate takes 0.16 s, and `check()` returns in 0.3 s (verified) to 0.5 s (rejected), so the warm REPL is optional. Lean's own error for a false claim only says the proposition is false, so `check()` returns a per-brick verdict (`explain`) telling the agent which brick failed.

**What ties it together:** the fact verifier confirms every fact literal in a certificate matches its DuckDB row (`row_sha256`), and that row points back into the image (path, offset).

### 7.2 Brute-force search in Lean (the miner)

The miner is a compiled Lean program (`lake exe mine facts.jsonl > bricks.jsonl`). The code below compiles as `lean/Miner.lean`; the `lake exe` wrapper is not written yet. For every approved set it:
1. enumerates **every combination of facts of the right kinds**,
2. keeps the combinations where `holds` returns true,
3. emits them as bricks.

```lean
import Std.Data.HashMap
open Std

structure Brick where
  claim : Claim
  cited : List Fact            -- the few facts this brick talks about

-- Generate: plain brute force over kind-filtered facts (USB/mount kinds are small)
def candUsbMounted (fs : Array Fact) : Array Brick := Id.run do
  let us := fs.filter (·.kind == .usbInsert)
  let ms := fs.filter (·.kind == .volumeMount)
  let mut out := #[]
  for u in us do
    for m in ms do
      out := out.push ⟨Sets.usbMountedAs u.id m.id, [u, m]⟩
  return out

-- Big kinds (fileCreated × fileModified): hash-join on the shared stud instead of nested loops
def candCopied (fs : Array Fact) : Array Brick := Id.run do
  let mut byPath : HashMap Nat (Array Fact) := {}
  for f in fs do
    if f.kind == .fileModified then
      byPath := byPath.insert f.obj ((byPath.getD f.obj #[]).push f)
  let mut out := #[]
  for c in fs do
    if c.kind == .fileCreated then
      for m in byPath.getD c.obj #[] do
        out := out.push ⟨Sets.copiedHere c.id m.id, [c, m]⟩
  return out

def candidates (fs : Array Fact) : Array Brick :=
  candUsbMounted fs ++ candCopied fs   -- ++ one generator per set

-- Test: keep only candidates that actually hold on their cited facts
def mine (fs : Array Fact) : List Brick :=
  (candidates fs).toList.filter (fun b => holds b.cited b.claim)

-- Soundness, proved once for ALL inputs: anything the miner emits holds.
theorem mine_sound {fs : Array Fact} {b : Brick} (h : b ∈ mine fs) :
    holds b.cited b.claim = true :=
  (List.mem_filter.mp h).2
```

Why this works:
- **Generate-and-test is sound by construction.** Generators can be as clever or as dumb as you like, even buggy. Only the `holds` filter decides, and `mine_sound` proves that. A generator bug can cause *misses*, never false bricks.
- **Brute force is affordable** because the loops run over kind-filtered facts. USB, mount, email and CD-burn kinds have tens to hundreds of rows, so nested loops are fine. Large kinds such as file timestamps are hash-joined on their shared stud. It's native code, and you can shard by time window if needed.
- **It's complete for the sets you have:** every instance of every approved set is found, not just the ones an LLM thought to look for. Report coverage per set.

### 7.3 Two ways to certify mined bricks
| Mode | How | Color | Use for |
|---|---|---|---|
| **Bulk** | Run `lake exe mine`. Every output is covered by `mine_sound`, but *running* compiled code trusts the Lean compiler (same as `native_decide`) | 🟧 | All mined bricks, instantly |
| **Kernel** | Codegen a certificate per brick (§7.1 B) and check `by decide` on its cited facts | 🟩 | Every brick that ends up in a narrative or the report |

Brute-force everything in bulk, then promote what matters to kernel-checked. The UI shows bricks changing color as they're promoted.

Measured: the kernel checks 1,000 two-fact bricks in one file in 0.8 s and 5,000 in 3.6 s. So every mined brick can be kernel-checked straight away. The 🟧 tier is only needed for claims the kernel can't evaluate, such as closed-world absence claims over the whole fact table.

### 7.4 Level 1 → 2+: forward-chaining (same brute force, one level up)
- **Story templates** are composite sets over sets, such as the exfil chain `usbMountedAs ⊕ openedFromMount ⊕ tagged ⊕ before`.
- The **chainer** is the same generate-and-test pattern, run in Lean over *bricks* instead of facts. It hash-joins bricks **only through shared studs** (same entity id) and **within a time window**. A composite's cited facts are the union of its children's.
- No cartesian products. Max depth 3, window ≤ 24 h by default.
- Soundness is the same one-line argument (`chain_sound`). Kernel promotion of a composite re-checks it over the union of cited facts (a few dozen) and assembles the proof with `holds_both`.

### 7.5 Where the LLMs come in
Brute force finds every instance of the patterns we *have*. The agents cover the rest:
- choose **which** composites matter, guided by the investigation questions;
- find patterns no current set covers, and propose **new sets** (§8.2), which the miner then brute-forces across the whole case;
- rank and explain. Not every true theorem matters: we show "e.g. 1,200 certified bricks → 8 narratives that answer the case questions."

### 7.6 Library schema (DuckDB `bricks` table)
| Column | Meaning |
|---|---|
| `brick_id`, `canonical_hash` | Dedup: nobody proves the same brick twice |
| `set_name`, `args`, `cited_fact_ids` | Which set, instantiated with which facts |
| `level`, `color` | Height in the proof graph, trust tier |
| `entities`, `t_min`, `t_max` | Studs for joining and time windows |
| `parents` | Child bricks it was snapped from (edges of the proof graph) |
| `lean_theorem`, `cert_json` | Certificate (empty until kernel-promoted) |
| `proposed_by` | `miner` / `chainer` / `agent:<name>` |

## 8. Agents: a lead investigator plus subagents

Centralized topology: one lead agent, specialist workers, and **no worker-to-worker chatter**. Workers share results only through the Lean-gated brick library (a blackboard).

### 8.1 Roles
| Agent | Spawned when | Does | Can write |
|---|---|---|---|
| **Lead investigator** | Always (main loop) | Turns the case questions into a plan; reads the library *index* (counts, entities, top bricks), not raw rows; spawns workers; composes narratives; writes the final ranking | Narratives via `check` |
| **Artifact specialists** (USB/registry, file system/LNK/jump lists, browser/search, email, Recycle Bin, CD burning) | In parallel at the start and when a question opens a new area | Explore their part of the DB; find patterns the miner's sets miss; flag gaps | Bricks via `check` |
| **Set designer** | When a specialist reports a gap | Drafts a new set: Lean `def` + miner generator + English template + strength label | Proposals to a **human review queue** |
| **Challengers** (adversarial) | One per candidate narrative | Try to certify the strongest alternative explanation (other device, user or time) | Counter-bricks via `check` |
| **Time-shard workers** (stretch) | Big images | Same as specialists, split by time window | Bricks via `check` |

### 8.2 The set-design loop (how the IR grows)
1. A specialist finds a pattern with no matching set. Example: "USB volume label matches a folder name in a Recycle Bin path."
2. The set designer drafts the Lean `def`, its miner generator and the English template.
3. Lean typechecks the definition. **Soundness can't break**, because sets only combine primitive checks and the miner always filters with `holds`.
4. A human approves the *interpretation* (English + strength) in the UI.
5. The miner brute-forces the new set across the whole case, and the chainer composes with it.

The LLM designs new brick shapes and Lean mass-produces them.

### 8.3 Spawn policy and budgets
- **Spawn only for parallel work that fits in a fresh context**, such as a separate artifact family or a separate alternative to test. Everything else stays in the lead loop.
- **Caps:** at most 6 concurrent workers, and each worker gets a turn/token budget.
- **Workers return** a summary of ≤ 200 words plus a list of brick ids, never transcripts. This keeps the lead agent's context clean.
- **Tools per worker:** read-only `sql`, `get_fact`, `library_search`, `check`. Only `check` writes, and only verified bricks.
- **Dedup:** `check` looks up the canonical hash first and returns the existing `brick_id` if it's already proven.

### 8.4 Tools
| Tool | Does |
|---|---|
| `sql(query)` | Read-only query over evidence DB + library |
| `get_fact(id)` | Full row + provenance |
| `library_search(entity / set / time)` | Find existing bricks to snap onto |
| `check(claim_json)` | Canonicalize → dedup → codegen → warm Lean REPL → insert brick or return the Lean error |
| `spawn(role, task, budget)` | Lead agent only: start a subagent (deepagents subagents / Claude Agent SDK subagents) |
| `propose_set(def, generator, template, strength)` | Set designer only: adds to the human review queue |
| `run_miner(sets?)` | Re-run the Lean miner (after a set is approved) |

### 8.5 Devil's advocate is built in
For every narrative, a challenger tries to certify the alternative, for example the authorized USB RM#1 instead of RM#2, or the CD-R instead of a USB. If both certify, the report shows both and says **"the evidence doesn't decide this."** That's what an investigator needs to know. If the alternative fails to certify, it is *not shown*, which is weaker than *refuted*: claims are positive, and there is no brick for "this did not happen" until closed-world absence bricks exist (§10).

## 9. Design rules (these matter)
1. **Only cited facts enter kernel proofs** (a brick's cited list, or a narrative's union). The compiled miner reads all facts, but certificates contain only what they cite. A verifier confirms each cited fact matches its DB row (`row_sha256`). Kernel cost depends on the size of the certificates, not the dataset.
2. **Intern every string to a `Nat`** in the extractor. The kernel compares numbers quickly; string comparisons can stall proof checking.
3. **Order claims must respect timestamp uncertainty.** `before` only certifies an order when the gap exceeds the *sum* of the two uncertainties. With true times anywhere within ±`res`, exceeding only the coarser one isn't enough: two FAT modification times stamped 3 s apart can be in either order. FAT modification times are only accurate to 2 s.
4. **Normalize to UTC at extraction** and keep the original timezone in provenance. NTFS stores UTC. FAT (RM#2) stores local time with no zone, and exFAT (RM#1) stores local time plus an offset, so FAT times must be converted using the PC's time zone from the registry. If this is wrong, every cross-device `before` is off by hours.
5. **The investigator reads English generated by templates from the claim tree, never by the LLM.** The sentence shown is exactly what Lean checked.
6. **Colors follow the weakest piece.** A narrative containing one 🟦 judgment tag is 🟦, and the UI says which brick caused it.
7. **Batch the Lean work:** one file can hold thousands of brick theorems (1,000 check in 0.8 s). Use `decide +kernel`: plain `decide` exceeds its recursion limit at 200 cited facts in one claim, and `decide +kernel` checks that case in 0.6 s. If a narrative's fact list grows well beyond that, split the narrative.

## 10. Stretch goals (in priority order)
1. **Re-derive facts from raw bytes.** The verifier re-reads each cited artifact at its offset in the image and re-hashes it, so the chain runs from image bytes to theorem.
2. **Time bounding for events with no timestamp** (after Gladyshev): certify bounds like "deleted between 15:02 and 15:10" from ordered neighboring bricks.
3. **Anomaly sets:** e.g. NTFS `$STANDARD_INFORMATION` created earlier than `$FILE_NAME` created (possible timestomping), or events after acquisition time.
4. **`holds_mono`:** done (`Theorems.lean`), together with `before_trans` and `before_asymm`: certified order is transitive and never runs both ways, so a certified timeline can't contradict itself.
5. **Completeness theorem for a set:** prove that `candUsbMounted` emits *every* matching pair, not just correct ones.
6. **Closed-world absence bricks** (🟧) for "no other device connected between T1 and T2."

## 11. Data: NIST CFReDS Data Leakage Case

- **Scenario:** insider IP theft. A Windows 7 Ultimate SP1 PC (20 GB, NTFS) plus three removable media:
  - RM#1: USB, 4 GB, exFAT. **This is the company's authorized USB for confidential files.**
  - RM#2: USB (SanDisk Cruzer Fit), 4 GB, FAT32.
  - RM#3: CD-R, 700 MB, UDF.
- **Why it fits:** the key question (which media carried what, when) is a join across device serials, volume serials, LNK targets and timestamps. That's exactly what bricks, studs and brute force are for, and keyword search can't answer it.
- **Downloads. Start now:**
  - PC image: `pc.E01–E04`, **7.28 GB**, readable directly by libewf / TSK / plaso. (The `pc.7z.001–003` set is 5.05 GB but needs 7-Zip and unpacks to a 20 GB raw image.)
  - RM#1 `.E01` 74.5 MB · RM#2 `.E01` 243 MB · RM#3 `.E01` 90.2 MB. **Develop against these first.**
  - `scripts/fetch_data.sh` downloads them (add `--pc` for the PC image).
  - URL: https://cfreds-archive.nist.gov/data_leakage_case/data-leakage-case.html
- **Answer key = eval:** https://cfreds-archive.nist.gov/data_leakage_case/leakage-answers.pdf
  - Includes a Q&A section and a minute-by-minute account of the suspect's actions. For example, on 2015-03-23 Chrome searches for "data leakage methods" around 14:02, and an email reading "Successfully secured." to the conspirator at 14:44.

### Metrics
- Baseline: Mulder's published scores on this case over 20 answer-key items (Claude Opus 4.6: 45% full match, 95% detection, 10% false positives). Score with the same items and definitions so the numbers are comparable.
- Answer-key questions answered by a certified narrative (coverage) and precision of certified findings
- Certified bricks by level and color: the "tower" chart, and 🟧 → 🟩 promotion count
- Per-set coverage from brute force (instances found per set)
- Share of LLM proposals rejected by Lean (the "hallucination firewall")
- Subagent efficiency: certified bricks per 1k tokens, duplicate-proposal rate
- Wall-clock from image to first certified narrative

## 12. How we score on the judging criteria

### Arlequin Track 1
| They want | We deliver |
|---|---|
| AI that finds what keyword search would miss | Brute-force stud joins across device serial ↔ volume serial ↔ LNK target ↔ copy signature ↔ timeline, plus agent-designed patterns |
| Results an investigator can check and trust, with evidence | Every brick and narrative has a certificate and a color; click down to path, offset and hash |
| Clear pipeline from raw data to insight | Image → facts → bricks → narratives → report, visible as one proof graph |
| Responsible compute | Compiled Lean miner does the bulk work with indexed joins; LLMs only rank, compose and design patterns; the kernel checks small certificates, not datasets; dedup prevents repeated proofs |
| Responsible data | Public NIST CFReDS data only |

### HackPrinceton rubric
- **Creativity:** Lean 4 as both the search engine and the proof language for evidence, with AI designing new brick shapes.
- **Utility:** works end to end on a real reference case with a published answer key.
- **Charity:** trustworthy, auditable AI for investigations; fewer wrong conclusions, faster backlogs.
- **Avidity:** the live proof tower, the rejection moment, and a set approved live during the demo.

## 13. Two-minute demo script
1. **(0:00–0:15) Problem.** "Investigators can't put an LLM summary in front of a court."
2. **(0:15–0:45) Run.** Start the case. The Lean miner brute-forces every pattern (bricks appear 🟧), six specialist subagents fan out, and bricks turn 🟩 as the kernel promotes them. A counter shows facts → bricks → narratives.
3. **(0:45–1:05) Zoom into a narrative.** "A confidential file was opened from an unauthorized USB after a leakage search." Expand it into bricks, then into raw artifacts with offsets. 🟩 except one 🟦 judgment tag, clearly labeled.
4. **(1:05–1:25) Key moment.** A subagent proposes "files burned to CD at 15:10." Lean rejects it and the brick never enters the library. The challenger's alternative gets no certificate either, and the report says so.
5. **(1:25–1:45) The IR grows.** The set designer proposes a new set, we approve it live, and the miner instantly brute-forces dozens more bricks with it.
6. **(1:45–2:00) Proof it works.** Answer-key coverage and rejection rate: "Every sentence in this report is a theorem."

## 14. Team plan (~30 h remaining)

| Role | Owns |
|---|---|
| **Data** | Downloads, ewf mount, plaso run, UTC + interning, deterministic tags, DuckDB, `facts.jsonl` export, fact verifier |
| **Lean** | Primitives + `holds` + `holds_both`, sets R2–R5 + English templates, **brute-force miner + `mine_sound`**, chainer, certificate codegen, color/axiom tiering |
| **Agents** | Lead loop + `spawn`, specialist/challenger/set-designer prompts, `check` with canonical-hash dedup + warm REPL, budgets, proposal log |
| **UI / demo** | Proof-graph view (bottom-up tower), timeline, certificate drawer, set-approval queue, eval scoreboard, video, Devpost |

**Agree on the `Fact` schema, `facts.jsonl` format and `Claim` JSON first.** They're the contract between all four roles.

### Milestones
| When | Milestone |
|---|---|
| Sat 1–3 AM | Start all downloads. Lean toolchain (elan + empty `lake` project, core only). Freeze `Fact` schema, `facts.jsonl`, `Claim` JSON. |
| Sat 3–10 AM | Extractor on RM images → DuckDB → `facts.jsonl`. Primitives + `holds` + `holds_both`. **Golden path: one hand-written brick and one 2-brick composite passing end to end by 10 AM.** |
| Sat 10 AM–2 PM | `lake exe mine` on RM facts for 3 sets → bulk 🟧 bricks in the library → kernel promotion batches. Lead agent loop with `check` (warm REPL). |
| Sat 2–7 PM | Subagents (specialists + challengers) via `spawn`; chainer with story templates; proof-graph UI. Full PC image extraction running. |
| Sat 7 PM–1 AM | Full case run, eval against answer key, set-designer loop + approval UI, scripted rejection demo. |
| Sun 1–5 AM | Stretch goals, README, harden the demo path, pre-compute a full run as backup. |
| Sun 5–8 AM | Record ≤2 min video, Devpost write-up, **submit before 8:00 AM**. |

## 15. Tech stack
- **Extraction:** libewf / `ewfmount`, The Sleuth Kit (`fls`, `istat`), plaso (`log2timeline` + `psort`), Python parsers as needed
- **Storage:** DuckDB (evidence DB + entity dictionary + brick library)
- **Lean:** Lean 4 via elan + lake, core library only (`Lean.Data.Json`, `Std.HashMap`). Compiled `lake exe mine` for brute force; Kimina Lean Server or LeanInteract as an optional warm REPL (cold checks already take 0.16 s).
- **Agents:** deepagents (built-in subagents, planning, filesystem; LangChain prize) or Claude Agent SDK subagents. Strongest available model for the lead agent and set designer, a cheaper model for specialists.
- **Backend/UI:** FastAPI + React (proof graph: a DAG view such as React Flow; timeline view)

### Repo layout
```
chain-of-proof/
├── lean/
│   ├── lakefile.toml           # libs ChainOfProof (trusted core) and Miner; exe `mine` to add
│   ├── ChainOfProof/
│   │   ├── Facts.lean          # Kind, Fact, Slot
│   │   ├── Claim.lean          # the brick IR
│   │   ├── Check.lean          # lookup, precedes, holds
│   │   ├── Sets.lean           # approved sets (named compositions)
│   │   ├── Theorems.lean       # holds_both, holds_mono, before_trans, …
│   │   └── Rules.md            # rules, strengths, templates, timestamp conventions
│   └── Miner.lean              # generators, mine, mine_sound (chainer to add)
├── checker/                    # check(): claim JSON → certificate .lean → kernel; English renderer
├── verifier/                   # cited facts ↔ DB rows, re-run kernel (↔ image bytes, stretch)
├── extractor/                  # schema.sql now; image → facts (DuckDB), UTC, interning, tags to add
├── fixtures/                   # synthetic sample facts + a sample certificate
├── tests/                      # end-to-end tests of checker and verifier
├── scripts/fetch_data.sh       # download the case images
├── certs/                      # generated certificates
├── agent/                      # lead loop + spawn, role prompts (to add)
├── ui/                         # proof graph, timeline, certificate drawer (to add)
├── eval/                       # answer-key questions + scorer (to add)
└── README.md
```

## 16. Risks and mitigations
| Risk | Mitigation |
|---|---|
| 5 GB image download / plaso run is slow | Start now; develop on the small RM images; restrict plaso parsers |
| Brute force too slow on big kinds | Kind filters, hash-joins on studs, shard by time window; it's compiled native code |
| Combinatorial explosion in chaining | Join only through shared studs, time windows, depth ≤ 3, story templates |
| Thousands of trivial theorems drown the signal | Lead agent ranks by case questions; UI shows narratives first, bricks on demand |
| Subagent cost / runaway loops | ≤ 6 concurrent, turn/token budgets, summaries only, cheaper model for specialists |
| Subagents duplicate work | Canonical-hash dedup in `check`; `library_search` before proposing |
| Errors spreading between agents | Workers share results only through the Lean-gated library, so one worker's mistake can't become another's premise |
| LLM-designed sets with misleading meaning | Sets can't break soundness; the English template + strength label require human approval |
| Lean slow on big certificates | Per-brick cited lists, batch files, parallel builds; fall back to `native_decide` badged 🟧 |
| `decide` gets stuck | Keep `holds` structurally recursive; intern strings to `Nat`; use `decide +kernel` (plain `decide` fails at 200 cited facts) |
| Timezone / clock confusion | UTC at extraction; original timezone in provenance; FAT times are local, so convert with the PC's zone |
| Demo fragility | Pre-computed full run as backup; scripted rejection and set-approval examples |

## 17. Submission checklist (from the hacker packet)
- [ ] Public GitHub repo **created between Nov 13 and Nov 15, 2026**
- [ ] Exactly **one** main track selected: Business & Enterprise
- [ ] Special tracks added: Arlequin Track 1, Amazon, LangChain deepagents (and the ChatOverflow agent connected)
- [ ] Optional (recommended) video ≤ 2 min, uploaded and linked on Devpost
- [ ] Discord usernames on the submission
- [ ] Ready for in-person demos (≤ 2 min) on Sunday, including special-track judges
- [ ] Submitted on Devpost **before 8:00 AM Sunday**

## 18. Sources
- Jagadeesan, Lubinski, Pitcher, Riely, Winebrinner. *Certificates for Verifiable Forensics*, IEEE CSF 2014 — https://reed.cs.depaul.edu/cpitcher/research/2014-csf-certificates-for-verifiable-forensics.pdf
- Gladyshev. *Adding real time into state machine analysis of digital evidence*, UCD 2006 — https://researchrepository.ucd.ie/entities/publication/4263b040-0f09-4bc5-9cac-695bb31f366d
- James, Gladyshev et al. *Analysis of Evidence Using Formal Event Reconstruction* — https://arxiv.org/abs/1302.2308
- NIST CFReDS Data Leakage Case — https://cfreds-archive.nist.gov/data_leakage_case/data-leakage-case.html
- NIST CFReDS Data Leakage Case answer key — https://cfreds-archive.nist.gov/data_leakage_case/leakage-answers.pdf
- Kim et al. *Towards a Science of Scaling Agent Systems* (Google Research / DeepMind / MIT) — https://research.google/blog/towards-a-science-of-scaling-agent-systems-when-and-why-agent-systems-work/
- Anthropic. *Building agents: When to fold subagents into your main agent loop* (Oct 2026) — https://www.claude.com/resources/articles/building-agents-when-to-fold-subagents-into-your-main-agent-loop
- Claude Agent SDK subagents — https://platform.claude.com/docs/en/agent-sdk/subagents
- LangChain deepagents — https://github.com/langchain-ai/deepagents
- AWS Open Source Blog. *Lean into verified software development* (Cedar) — https://aws.amazon.com/blogs/opensource/lean-into-verified-software-development
- BlueTeamCon 2026 talk on AI in incident response — https://blueteamcon2026.sched.com/event/2P73v
- GenDFIR (LLM + RAG timeline analysis) — https://arxiv.org/abs/2409.02572
- Mulder report on the NIST Data Leakage Case — https://calebevans.github.io/mulder/examples/nist-data-leakage/sonnet/nist-data-leakage.report.html
- Mulder (`mulder-dfir`) benchmark table and anti-hallucination design — https://pypi.org/project/mulder-dfir/
- Kimina Lean Server — https://arxiv.org/abs/2504.21230

## 19. Corrections in v3.1

Each of these was found by compiling the sketch on Lean 4.35.0 or by checking a claim against its source.

| # | Was | Now | Why |
|---|---|---|---|
| 1 | `before` required a gap larger than `max x.res y.res` | Larger than `x.res + y.res` | With true times within ±`res`, the `max` rule can certify an order that didn't happen |
| 2 | `holds` used `decide (… < …)`, `max`, `==` on `Nat`, two-discriminant matches | `Nat.beq`, `Nat.blt`, `with1` / `with2` | The old form made every certificate depend on `propext`, so "no extra axioms" was false |
| 3 | `native_decide` detected by `Lean.ofReduceBool` | Any axiom outside the standard three; `sorryAx` means failure | Lean 4.35 names the axiom per theorem |
| 4 | Certificates proved `by decide` | `by decide +kernel` | Plain `decide` hits its recursion limit at 200 cited facts |
| 5 | `openedFromMount` didn't require `m` to be a volume mapping | Adds `.is m .volumeMount` | Any fact sharing the volume id would have satisfied it |
| 6 | `copiedHere` joined created/modified on path only | Also joins on volume | The same path on two volumes was treated as one file |
| 7 | Tag facts had no stated time | `t` = when the tag was assigned | With `t = 0`, `before tag event` would certify |
| 8 | "If the challenger's alternative fails, the narrative stands" | Failing to certify is "not shown", not "refuted" | Claims are positive only |
| 9 | Mulder described as writing narratives you re-check by hand | Mulder validates that citations exist and publishes answer-key scores | Its own documentation; the gap we fill is whether the citation supports the sentence |
| 10 | `holds_mono` listed as a stretch goal | Proved, with `before_trans` and `before_asymm` | |
| 11 | Warm REPL and a bulk 🟧 tier assumed necessary for speed | Optional | Cold check 0.16 s; 1,000 bricks kernel-checked in 0.8 s |
| 12 | PC image as 5.05 GB 7z; RM#2 as 7z | E01 sets, read directly | No 7-Zip step, no 20 GB raw file |
| 13 | UTC normalization stated without the FAT caveat | FAT stores local time; convert with the PC's zone | Cross-device ordering depends on it |
| 14 | One color per brick | Two fields: `trust_tier` and `strength` | How it was checked and how strong the rule is are independent |
