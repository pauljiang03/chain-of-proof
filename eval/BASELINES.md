# Baselines on the NIST CFReDS Data Leakage Case

Collected by a search agent on 2026-11-14 from the pages linked below. Numbers are
quoted as published. Every one of them is self-reported by the tool's authors; we found
no independent or peer-reviewed score on this case. We have not re-run any of them.

## Same case

| System | Kind | Published result | How it was scored |
|---|---|---|---|
| [Mulder 1.5.2](https://github.com/calebevans/mulder/tree/main/examples/ndlc-v1.5.2), Claude Opus 4.6 | AI agent | 45% full match (45–50), 95% detection (90–95), 10% false positives (5–10), 68–79 min; median of 3 runs | Its own 20 items (below) |
| Mulder, Kimi K3 | AI agent | 35% (35–50) / 90% (80–95) / 20% (20–25), 52–70 min | Same |
| Mulder, GLM-5 | AI agent | 20% (20–25) / 75% (75–90) / 20% (10–25), 60–63 min | Same |
| [TRUDI](https://github.com/nebulae/trudi/blob/main/cases/cfreds-leak/reports/CFREDS-LEAK_accuracy_report.md) | AI agent | precision 13/13, recall 17/28 | Its own 28 items, rebuilt from memory of the key |
| [FORENSIA](https://speakerdeck.com/sumeshi/forensia-local-llm-forensic-harness) | Local LLM | 8 / 12 | The subset of questions its tool supports |
| [Cold Box](https://github.com/at-src/cold-box/blob/main/docs/ACCURACY.md), Claude Sonnet 4.6 | AI agent | 4/4 required checks, about 27 min, PC image only | Keyword checks |
| [RepertIA 3.0.2](https://github.com/silvexe/RepertIA/blob/main/docs/prove/nist-data-leakage.md) | No AI | 53 of NIST's 60 questions answered as NIST does | Self-checked; seven tool defects were fixed using this case |
| [deciban](https://huggingface.co/datasets/IcyApril/deciban) (arXiv 2607.17384) | Open-weight models as agents | best 26.5% single try, pooled over five challenges (58 of its 98 questions are this case) | Per-case numbers are not public |

Mulder's metric definitions, quoted from its scorecards: "a wrong detail (edition, date,
timezone, device) is PARTIAL, mention without evidence is PARTIAL, and only claims the
answer key contradicts or causal attributions the evidence does not support count as
FALSE POSITIVE." Full match is FOUND/20; detection is (FOUND+PARTIAL)/20; the
false-positive rate is contradicted claims/20 and includes claims outside the 20 items.
No timestamp tolerance is stated.

Mulder's 20 scored items (text from `opus-4.6-run1/ACCURACY-REPORT.md`):

1. Suspect identity: "Iaman Informant" (iaman.informant@nist.gov)
2. PC OS: Windows 7 Ultimate 64-bit, standalone WORKGROUP
3. USB Device 1: SanDisk Cruzer Fit, S/N 4C530012450531101593, exFAT, "Authorized USB"
4. USB Device 2: SanDisk Cruzer Fit, S/N 4C530012550531106501, FAT32, "IAMAN $_@"
5. RM3: CD-ROM, UDF filesystem, formatted March 24, 2015 (16:53:17 UTC)
6. Five Secret Project documents exfiltrated to USB
7. File masquerading: documents renamed with false extensions on RM2 FAT32
8. Anti-forensics tools: CCleaner and Eraser deployed
9. Search history reveals premeditation (leakage methods, anti-forensics)
10. Google Drive sync installed for cloud exfiltration
11. iCloud setup downloaded (secondary cloud channel)
12. USB connection timestamps via EVTX System log
13. Exfiltration timeline: Feb 15 bulk copy (42-second window)
14. Anti-forensics: CCleaner deployed but did not clean (launched and closed without action)
15. Systematic file deletion on RM2 FAT32 (Mar 24, 09:54–10:00)
16. RM3 contains government documents matching Secret Project content
17. Files opened in RM2 (list all accessed files)
18. Network drive directories traversed
19. Email communication with spy.conspirator@nist.gov
20. FAT32 timezone offset (local time vs UTC)

## How often AI-written forensic reports say more than the evidence

| Source | Measured |
|---|---|
| Android forensic reports, arXiv 2610.26946 | 28.07% of 595 claims not grounded (by model: 20.70% to 40.69%) |
| Mulder on this case | 1 to 5 contradicted claims per report |
| Agent-log forensics, arXiv 2610.09581 | unsupported source assertions in 26 of 28 cases |
| Our own plain-report test (`runs/report-audit`) | 24 of 50 sentences said more than the records certify; 0 contradicted |

## What Mulder's award establishes

SANS awarded Mulder first place in Find Evil! 2026 after a competition-wide 1,775
practitioner evaluations of 123 finalists by 90 reviewers. Its announcement emphasizes
Mulder's five-phase investigation, evidence citations, adversarial self-challenge and
a logged investigation spanning 11 systems and 120 GB. This is practitioner validation
of the system; it is not a common 60-question NIST accuracy ranking.
[SANS announcement](https://www.sans.org/press/announcements/sans-names-the-five-winners-of-find-evil-2026).

Judging equally weighted autonomous execution, IR accuracy, breadth/depth, architectural
constraints, audit trails and usability/documentation.
[Competition rules](https://findevil.devpost.com/rules).

Our conservative crosswalk finds about 16 numbered question topics behind Mulder's
20 criteria: Q3, Q4, Q11, Q16, Q20, Q21, Q22, Q26, Q27, Q29, Q33, Q52, Q53, Q54,
Q55 and Q56. This is our interpretation, not an official one-to-one mapping. Q22
feeds three criteria; some criteria add scenario-level interpretation or claims with
no exact numbered-question counterpart. It does not mean 16 complete questions are tested.

## What is comparable

- Same case, different contracts: Mulder's repeated 20-item checklist and RepertIA's
  per-question count. Neither can be directly ranked against our 613-item coverage.
- In kind only: scores on other disk images (TRUDI and verdict-dfir on the NIST Hacking
  Case; SecRespond), and the hallucination rates above.
- Known answer-key quirks, reported independently by RepertIA and by our own
  transcription: the burn event is 133 in the data where the key prints 113, and two
  of the key's tables are one hour off.

The [new typed reference](benchmark_nist.json) is a draft expansion to all 60 questions.
It needs independent review before supporting a controlled comparison. Our archived
LLM regrades are not benchmark scores; see [the evaluation contract](EVALUATION.md).
