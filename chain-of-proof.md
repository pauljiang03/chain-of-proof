# Chain of Proof

**Machine-checked digital forensics: the LLM proposes, Lean 4 decides.**

> "Every sentence in our report is a theorem."

HackPrinceton Fall '26 project spec. Submissions are due **Sun Nov 15, 8:00 AM** (hard deadline). Judging runs 9:30 AM – 2:30 PM.

---

## 1. One-liner

An AI forensic investigator that never puts an unverified claim in front of the investigator. An LLM agent searches a disk image and proposes findings. Each finding is written in a small **Lean 4 intermediate representation (IR)**. The Lean kernel checks it against facts pulled from the image by deterministic tools. Only findings that pass become part of the report, and each comes with a certificate listing the exact artifacts and rules it relies on.

## 2. Tracks

| Track | Why we fit |
|---|---|
| **Main: Business & Enterprise** | The track description explicitly lists cybersecurity and privacy |
| **Arlequin AI – Track 1: AI-Driven Forensics** | Built for their criteria (see §10) |
| Amazon – Best Practical AI Innovation | Agentic: reasons, plans, acts, adapts to verifier feedback |
| LangChain – Best use of deepagents | Build the agent loop on deepagents |
| ChatOverflow leaderboard | Free entry: connect our coding agent |

## 3. Problem

- **Investigators can't trust LLM output.** Incident response findings feed legal proceedings, regulatory responses and executive decisions. One fabricated timeline entry or wrong attribution can leave a backdoor in place or send people after the wrong suspect. (Source: BlueTeamCon 2026 talk on AI in IR.)
- **Existing LLM forensics tools write narratives.** Examples are GenDFIR (RAG plus LLM timeline analysis) and Mulder, an open-source agent that has already produced an incident report on the same NIST case we use. You still have to re-check the narrative by hand.
- **Case backlogs keep growing** while the number of devices per case rises. Investigators need speed *and* rigor.

## 4. Core idea: Lean 4 as the IR between search and verification

```
LLM (untrusted)  ──proposes──►  Claim (Lean IR)  ──checked by──►  Lean kernel (trusted)
                                     ▲
           cites facts extracted by deterministic forensic tools (trusted, reproducible)
```

- **Search is hard and fuzzy**, so the LLM does it.
- **Checking is easy and exact**, so Lean does it.
- **The certificate sits in between**: claim, cited facts, rules used and proof. Anyone can re-check it without re-running the search.

### Prior art we build on
- **Certificates for Verifiable Forensics** (Jagadeesan, Pitcher, Riely et al., DePaul, IEEE CSF 2014). Proposes *forensic certificates* as intermediate artifacts between search and verification, to shrink the trusted computing base. They formalized a Honeynet rootkit case in Coq by hand. **We automate the search side with an LLM agent and use Lean 4 as the certificate language.**
- **Gladyshev & Patel, finite-state-machine event reconstruction** (2004–2006). Formal event reconstruction, including computing time bounds for events whose time is unknown from witness observations with known times. This is our stretch feature (§8).
- **Lean-as-IR in industry:** AWS Cedar models its policy engine in Lean, proves properties and differentially tests the Rust production code against the Lean model. Lean evaluates a test input in about 5 µs.

## 5. Architecture

```
┌────────────┐   ┌──────────────────────┐   ┌───────────────────────────┐
│ Disk image │──►│ [1] Extractor         │──►│ Evidence DB (DuckDB)      │
│ (E01 / DD) │   │ Sleuth Kit, plaso,    │   │ facts + provenance        │
└────────────┘   │ python parsers        │   │ (image, path, offset,     │
                 │ normalize → UTC       │   │  tool, row sha256)        │
                 │ intern strings → Nat  │   └─────────────┬─────────────┘
                 └──────────────────────┘                 │ SQL
                                                          ▼
                 ┌──────────────────────────────────────────────────────┐
                 │ [3] Agent loop (single loop, deepagents / Agent SDK) │
                 │ tools: sql · get_fact · check · print_axioms         │
                 │ proposes Claim ──► Lean ──► errors back ──► revise   │
                 └───────────────┬──────────────────────────────────────┘
                                 ▼
          ┌──────────────────────────────────────────────┐
          │ [2] Lean checker (core Lean 4, no Mathlib)   │
          │ Fact / Claim / holds / Rules                 │
          │ `theorem F7 : holds cited claim = true`      │
          └───────────────┬──────────────────────────────┘
                          ▼
   ┌────────────────────────────────────────────────────────────┐
   │ [4] Certificate + report                                   │
   │ English rendered from the claim by templates (no LLM)      │
   │ cited artifacts · rules used · trust tier · kernel status  │
   └────────────────────────────────────────────────────────────┘
```

### Trust boundary
| Component | Trusted? | Why |
|---|---|---|
| Extractor (TSK, plaso, parsers) | Yes | Community-validated, deterministic, re-runnable |
| Rule library (≈5–10 rules) | Yes, *as stated assumptions* | Small, human-reviewed, listed in every certificate |
| Lean kernel | Yes | Small trusted kernel |
| Fact verifier script | Yes | ~100 lines; re-checks cited facts against the DB |
| **LLM agent** | **No** | Can be wrong; can't get a wrong claim into the report |

## 6. The IR (Lean 4 sketch)

> This is a sketch: adjust field names to the real artifacts. Use **core Lean only, no Mathlib**. That cuts setup time and download size.

```lean
-- ChainOfProof/Facts.lean  (generated by the extractor, never by the LLM)
inductive Kind where
  | usbInsert     -- USBSTOR / setupapi: device serial seen
  | volumeMount   -- registry join: device serial ↔ volume serial
  | lnkTarget     -- LNK / jump list: target path on volume serial
  | fileCreated | fileModified | fileDeleted
  | webSearch | emailSent | cdBurn
  deriving DecidableEq, Repr

structure Fact where
  id   : Nat   -- row id in evidence DB
  kind : Kind
  t    : Nat   -- UTC microseconds since epoch
  res  : Nat   -- timestamp resolution in µs (NTFS≈1, exFAT=10_000, FAT mtime=2_000_000)
  obj  : Nat   -- interned primary object (path / device serial / query string)
  aux  : Nat   -- interned secondary object (volume serial, target path, …)
  deriving DecidableEq, Repr

-- ChainOfProof/Claim.lean  (the IR the LLM writes)
inductive Claim where
  | before     (a b : Nat)              -- a happened before b, beyond timestamp resolution
  | sameDevice (usb mount : Nat)        -- R1+R2: USB insert and volume mapping share a device serial
  | onVolume   (lnk vol : Nat)          -- R3: LNK target lives on volume serial `vol`
  | copied     (created modified : Nat) -- R4 (heuristic): created > modified ⇒ copied here
  | both       (c d : Claim)
  deriving Repr

def lookup (fs : List Fact) (i : Nat) : Option Fact := fs.find? (·.id == i)

-- Keep `holds` structurally recursive so `decide` can evaluate it in the kernel.
def holds (fs : List Fact) : Claim → Bool
  | .before a b =>
    match lookup fs a, lookup fs b with
    | some x, some y => decide (x.t + max x.res y.res < y.t)
    | _, _ => false
  | .sameDevice u m =>
    match lookup fs u, lookup fs m with
    | some x, some y => x.kind == .usbInsert && y.kind == .volumeMount && x.obj == y.obj
    | _, _ => false
  | .onVolume l v =>
    match lookup fs l with
    | some x => x.kind == .lnkTarget && x.aux == v
    | none => false
  | .copied c m =>
    match lookup fs c, lookup fs m with
    | some x, some y => x.kind == .fileCreated && y.kind == .fileModified
                        && x.obj == y.obj && decide (y.t < x.t)
    | _, _ => false
  | .both c d => holds fs c && holds fs d

-- certs/F7.lean  (generated per finding)
def cited : List Fact := [
  ⟨4512, .usbInsert,   1427119200000000, 1, 101, 0⟩,
  ⟨4513, .volumeMount, 1427119201000000, 1, 101, 88⟩,
  ⟨4600, .lnkTarget,   1427120900000000, 1, 913, 88⟩ ]

def claimF7 : Claim := .both (.sameDevice 4512 4513) (.onVolume 4600 88)

theorem F7 : holds cited claimF7 = true := by decide
#print axioms F7   -- should depend on no axioms → "kernel-checked" tier
```

### Design rules (these matter)
1. **Only cited facts go into Lean.** The evidence DB can have millions of rows; a certificate has a few dozen. A separate verifier confirms each cited fact matches its DB row (`row_sha256`). Checking cost depends on the size of the claim, not the dataset (Arlequin's "responsible compute").
2. **Intern every string to a `Nat` in the extractor.** The Lean kernel compares numbers quickly; string comparisons can stall proof checking.
3. **Rules are stated assumptions, each with a strength label:**

   | Rule | Meaning | Strength |
   |---|---|---|
   | R1 | A USBSTOR/setupapi record means a device with this serial was connected | Strong (artifact semantics) |
   | R2 | A registry mapping links device serial → volume serial | Strong |
   | R3 | An LNK/jump-list entry means its target path on volume V was opened by user U | Strong |
   | R4 | Windows copy keeps modified time and sets a new created time, so created > modified ⇒ copied | **Heuristic** |
   | R5 | A Recycle Bin `$I` record gives the deletion time of the original path | Strong |

4. **Order claims must respect timestamp resolution.** `before` only certifies an order when the gap exceeds the coarser resolution. FAT stores modification times only to 2 s.
5. **Normalize all timestamps to UTC at extraction** and store the original timezone in provenance.
6. **Proof strength is shown automatically.** A finding proved by `decide` relies only on the kernel. One that needed `native_decide` also trusts the compiler, because `#print axioms` shows `Lean.ofReduceBool`. The UI badges it automatically.
7. **The investigator reads English generated by templates from the claim tree, never by the LLM.** So the sentence shown is exactly what Lean checked. This avoids the "compiles but doesn't mean what the English says" problem.

   | Claim | English template |
   |---|---|
   | `before a b` | "{a} happened before {b} (gap {Δ} > resolution {r})" |
   | `sameDevice u m` | "USB device {serial} was connected and mounted as volume {vol}" |
   | `onVolume l v` | "{user} opened {path} from volume {vol}" |
   | `copied c m` | "{path} was likely copied to this location (created after last modified) — heuristic R4" |

### Certificate format (`certs/F7.json`)
```json
{
  "finding_id": "F7",
  "question": "Which device received the confidential files?",
  "english": "USB device 4C530012550531106501 was connected and mounted as volume …; Mr. Informant opened [secret_project]_design_concept.ppt from that volume.",
  "claim": {"both": [{"sameDevice": [4512, 4513]}, {"onVolume": [4600, 88]}]},
  "cited_facts": [
    {"id": 4512, "row_sha256": "…", "prov": {"image": "pc.E01", "artifact": "SYSTEM\\ControlSet001\\Enum\\USBSTOR\\…", "offset": 0, "tool": "plaso"}}
  ],
  "rules": ["R1", "R2", "R3"],
  "lean_file": "certs/F7.lean",
  "trust_tier": "kernel",
  "status": "verified"
}
```

## 7. Agent loop

A **single loop**, not a multi-agent org chart. Tools:

| Tool | Does |
|---|---|
| `sql(query)` | Read-only query over the evidence DB (DuckDB) |
| `get_fact(id)` | Full row + provenance |
| `check(claim_json, fact_ids)` | Generates `certs/Fx.lean`, compiles it with Lean, returns pass or the Lean error |
| `print_axioms(finding)` | Returns the trust tier |

Flow per investigative question:
1. Explore with SQL and form a hypothesis.
2. Write a `Claim` that cites fact ids, then call `check`.
3. If Lean rejects it, read the error and revise or abandon the claim. **A rejected claim never reaches the report.**
4. **Devil's advocate pass:** try to certify the strongest competing explanation (e.g., authorized USB RM#1 vs. unauthorized RM#2 vs. CD-R). If both pass, report that *the evidence doesn't decide this*, which is what an investigator actually needs to know.
5. Log every proposal and rejection. Rejections are part of the demo.

## 8. Stretch goals (in priority order)
1. **Re-derive facts from raw bytes.** The verifier re-reads each cited artifact at its offset in the image and re-hashes it, so the whole chain goes from image bytes to theorem.
2. **Time bounding for events with no timestamp** (after Gladyshev). Certify bounds such as "the deletion happened between 15:02 and 15:10" from ordered neighboring events.
3. **Anomaly invariants:** certify violations as findings, e.g. NTFS `$STANDARD_INFORMATION` created earlier than `$FILE_NAME` created (possible timestomping), or events after acquisition time.
4. **Prove a soundness lemma about the checker,** e.g. `holds fs (.both c d) = true → holds fs c = true`.

## 9. Data: NIST CFReDS Data Leakage Case

- **Scenario:** insider IP theft. A Windows 7 Ultimate SP1 PC (20 GB, NTFS) plus three removable media:
  - RM#1: USB, 4 GB, exFAT. **This is the company's authorized USB for confidential files.**
  - RM#2: USB (SanDisk Cruzer Fit), 4 GB, FAT32.
  - RM#3: CD-R, 700 MB, UDF.
- **Why it fits:** the key question (which media carried what, when) is a join across device serials, volume serials, LNK targets and timestamps. Keyword search can't answer it.
- **Downloads. Start now:**
  - PC image: `pc.7z.001–003`, **5.05 GB compressed**. This is the slow one.
  - RM#1 `.E01` 74.5 MB · RM#2 `.7z` 219 MB · RM#3 `.E01` 90.2 MB. **Develop against these first.**
  - URL: https://cfreds-archive.nist.gov/data_leakage_case/data-leakage-case.html
- **Answer key = eval:** https://cfreds-archive.nist.gov/data_leakage_case/leakage-answers.pdf
  - Includes a Q&A section and a minute-by-minute account of the suspect's actions. For example, on 2015-03-23 Chrome searches for "data leakage methods" around 14:02, and an email reading "Successfully secured." to the conspirator at 14:44.
  - **Metrics:**
    - Answer-key questions answered with a verified certificate
    - Precision of certified findings against the answer key
    - Share of LLM proposals rejected by Lean (shows the "hallucination firewall" working)

## 10. How we score on the judging criteria

### Arlequin Track 1
| They want | We deliver |
|---|---|
| AI that finds what keyword search would miss | Multi-artifact joins: device serial ↔ volume serial ↔ LNK target ↔ copy signature ↔ timeline |
| Results an investigator can check and trust, with evidence | Every finding has a certificate: cited artifacts (path, offset, hash), rules used, kernel status |
| Clear pipeline from raw data to insight | Image → facts → claims → certificates → report |
| Responsible compute | LLM sees query results, not raw images; Lean checks certificates, not datasets |
| Responsible data | Public NIST CFReDS data only |

### HackPrinceton rubric
- **Creativity:** Lean 4, the language behind recent AI math results, used as an IR for forensic evidence.
- **Utility:** works end to end on a real reference case with a published answer key.
- **Charity:** trustworthy, auditable AI for investigations; fewer wrong conclusions, faster backlogs.
- **Avidity:** show the live rejection moment and the eval score.

## 11. Two-minute demo script
1. **(0:00–0:20) Problem.** "Investigators can't put an LLM summary in front of a court. One hallucinated timeline entry ruins a case."
2. **(0:20–0:50) Run.** Load the NIST Data Leakage Case and start the agent. The timeline fills with green-checked findings.
3. **(0:50–1:15) Certificate.** Click a finding. The drawer shows four artifacts with offsets and hashes, rules R1–R3, and "verified by the Lean kernel, no extra axioms."
4. **(1:15–1:40) Key moment.** The LLM proposes a plausible but false claim ("files burned to CD at 15:10"). Lean rejects it, the agent revises, and the false claim never reaches the report.
5. **(1:40–2:00) Proof it works.** Answer-key score, rejection rate, and "every sentence in this report is a theorem."

## 12. Team plan (~30 h remaining)

| Role | Owns |
|---|---|
| **Data** | Downloads, ewf mount, plaso run (only needed parsers), normalize to UTC, intern ids, DuckDB, fact verifier |
| **Lean** | `Kind` / `Fact` / `Claim` / `holds`, rules R1–R5, English templates, certificate generator, `#print axioms` tiering |
| **Agent** | Agent loop on deepagents (or Claude Agent SDK), tools, devil's-advocate pass, proposal/rejection log |
| **UI / demo** | Timeline view, certificate drawer, eval scoreboard, video, Devpost |

**Agree on the `Fact` schema first.** It's the contract between the Data and Lean roles.

### Milestones
| When | Milestone |
|---|---|
| Sat 1–3 AM | Start all downloads. Install the Lean toolchain (elan, empty `lake` project, core only). Freeze the `Fact` schema. |
| Sat 3 AM–noon | Extractor on RM images → DuckDB. Lean checker + R1–R3. **Golden path: one hand-written certificate passing end to end by noon.** |
| Sat noon–6 PM | Agent loop + `check` tool. UI timeline + certificate drawer. Full PC image extraction running. |
| Sat 6 PM–midnight | Full case run, eval against answer key, devil's-advocate pass, scripted rejection demo. |
| Sun midnight–5 AM | Stretch goals, README, harden the demo path. |
| Sun 5–8 AM | Record ≤2 min video, Devpost write-up, **submit before 8:00 AM**. |

## 13. Tech stack
- **Extraction:** libewf / `ewfmount`, The Sleuth Kit (`fls`, `istat`), plaso (`log2timeline` + `psort`), Python parsers as needed
- **Storage:** DuckDB
- **Lean:** Lean 4 via elan + lake, core library only. Optionally Kimina Lean Server or LeanInteract for fast programmatic checks.
- **Agent:** deepagents (LangChain prize) or Claude Agent SDK; strongest available model for claim writing
- **Backend/UI:** FastAPI + a React timeline view

### Repo layout
```
chain-of-proof/
├── extractor/            # image → facts (DuckDB), UTC normalization, interning
├── lean/
│   ├── lakefile.toml
│   └── ChainOfProof/
│       ├── Facts.lean    # Kind, Fact
│       ├── Claim.lean    # Claim IR
│       ├── Check.lean    # lookup, holds
│       └── Rules.md      # R1–R5 with strength labels + English templates
├── certs/                # generated F*.lean + F*.json
├── verifier/             # cited facts ↔ DB rows (↔ image bytes, stretch)
├── agent/                # loop + tools
├── ui/
├── eval/                 # answer-key questions + scorer
└── README.md
```

## 14. Risks and mitigations
| Risk | Mitigation |
|---|---|
| 5 GB PC image download / plaso run is slow | Start now; develop on the small RM images; restrict plaso parsers |
| Lean slow on large fact files | Only cited facts enter Lean; intern strings to `Nat` |
| `decide` gets stuck | Keep `holds` structurally recursive; fall back to `native_decide` and badge it as a weaker tier |
| Claim says something different from the English | English comes from fixed templates over the claim, never from the LLM |
| Rules are wrong or too strong | Rules are few, labeled strong/heuristic, and listed in every certificate |
| Timezone / clock confusion | Normalize to UTC at extraction; keep original timezone in provenance |
| Agent can't find the right fact ids | `sql` tool + a few worked examples in the prompt; hand-write the golden certificate first |
| Demo fragility | Pre-compute the full run; keep a scripted rejection example ready |

## 15. Submission checklist (from the hacker packet)
- [ ] Public GitHub repo **created between Nov 13 and Nov 15, 2026**
- [ ] Exactly **one** main track selected: Business & Enterprise
- [ ] Special tracks added: Arlequin Track 1, Amazon, LangChain deepagents (and the ChatOverflow agent connected)
- [ ] Optional (recommended) video ≤ 2 min, uploaded and linked on Devpost
- [ ] Discord usernames on the submission
- [ ] Ready for in-person demos (≤ 2 min) on Sunday, including special-track judges
- [ ] Submitted on Devpost **before 8:00 AM Sunday**

## 16. Sources
- Jagadeesan, Lubinski, Pitcher, Riely, Winebrinner. *Certificates for Verifiable Forensics*, IEEE CSF 2014 — https://reed.cs.depaul.edu/cpitcher/research/2014-csf-certificates-for-verifiable-forensics.pdf
- Gladyshev. *Adding real time into state machine analysis of digital evidence*, UCD 2006 — https://researchrepository.ucd.ie/entities/publication/4263b040-0f09-4bc5-9cac-695bb31f366d
- James, Gladyshev et al. *Analysis of Evidence Using Formal Event Reconstruction* — https://arxiv.org/abs/1302.2308
- NIST CFReDS Data Leakage Case — https://cfreds-archive.nist.gov/data_leakage_case/data-leakage-case.html
- NIST CFReDS Data Leakage Case answer key — https://cfreds-archive.nist.gov/data_leakage_case/leakage-answers.pdf
- AWS Open Source Blog. *Lean into verified software development* (Cedar) — https://aws.amazon.com/blogs/opensource/lean-into-verified-software-development
- BlueTeamCon 2026 talk on AI in incident response — https://blueteamcon2026.sched.com/event/2P73v
- GenDFIR (LLM + RAG timeline analysis) — https://arxiv.org/abs/2409.02572
- Mulder report on the NIST Data Leakage Case — https://calebevans.github.io/mulder/examples/nist-data-leakage/sonnet/nist-data-leakage.report.html
- Kimina Lean Server — https://arxiv.org/abs/2504.21230
- LangChain deepagents — https://github.com/langchain-ai/deepagents
