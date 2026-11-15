# CONAN-F

**An AI forensic investigator. Lean 4 checks every finding.**

CONAN-F reads disk images and makes a store of records. An AI investigator searches the
records and proposes findings. The Lean 4 kernel accepts a finding only when the cited
records prove it. The report and the app show only accepted findings.

## Open the app

```sh
git clone https://github.com/pauljiang03/conan && cd conan && ./install.sh
```

## Results

Each investigation had a 15-minute budget. A fixed scorer compared the answers with the
expected answers. It does not use an AI judge.

| Case | Fully correct | Partial | Unanswered | Incorrect | Answer fields matched |
|---|---:|---:|---:|---:|---:|
| Hacking Case | 11/31 (35.5%) | 0 | 20 | 0 | 13/52 (25%) |
| Data Leakage | 6/46 (13.0%) | 10 | 30 | 0 | 306/1,627 (18.8%) |

## How it works

1. **Read.** Readers make records from the disk images.
2. **Investigate.** The AI investigator searches the records and proposes claims.
3. **Check.** The checker converts each claim to Lean code. The Lean kernel accepts or refuses it.
4. **Verify.** A second checker, con-leche, checks the proofs again.

A proof does not show that a reader read the disk image correctly, or who used a device.
