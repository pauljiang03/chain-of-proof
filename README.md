# CONAN-F

**An AI forensic investigator. Lean 4 checks every finding.**

## Motivation

Imagine you give an AI a complete criminal investigation, and it works through the evidence
on its own. It searches the disk images, follows leads, and reconstructs the events.
Investigators can then spend their time on the evidence that matters, and close cases faster.

## What we solve

AI can hallucinate, and a citation alone does not make a conclusion true. A forensic finding
goes to court, so an investigator must be able to check it. CONAN-F lets the AI do the
investigative work, but it keeps only the findings that the evidence proves.

## How we solve it

1. **Read.** Readers make records from the disk images.
2. **Investigate.** The AI investigator searches the records, follows leads, and proposes claims.
3. **Check.** The checker converts each claim to Lean 4, a mathematical proof assistant. Lean
   accepts a claim only when the cited records prove it. If the AI links a file to the wrong
   USB drive, Lean finds that the identifiers do not agree and refuses the claim.
4. **Verify.** A second checker, con-leche, checks each proof again.

The app shows the accepted findings as a summary, a timeline of events, and a proof graph that
connects each finding to its records and to the disk image. It also makes a forensic
examination report that investigators can review and export.

## Open the app

```sh
git clone https://github.com/pauljiang03/conan && cd conan && ./install.sh
```

On a Mac, this adds **Conan** to your Applications folder and opens it.
