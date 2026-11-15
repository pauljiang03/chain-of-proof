# CONAN-F

**An AI forensic investigator. Lean 4 checks every finding.**

## Motivation

A forensic investigator must examine a large quantity of evidence. An AI investigator can do
much of this work. It can search the disk images, find connections, and show the sequence of
events. Then the investigator can use more time on the important evidence and complete cases
quickly.

## What we solve

An AI can state facts that are not in the evidence. A citation alone does not make a
conclusion true. An investigator must be able to check each finding. CONAN-F lets the AI do the investigation, but it keeps only the findings that the
evidence proves.

## How we solve it

1. **Read.** Readers make records from the disk images.
2. **Investigate.** The AI investigator searches the records, finds connections, and proposes claims.
3. **Check.** The checker converts each claim to Lean 4, a mathematical proof assistant. Lean
   accepts a claim only when the cited records prove it. For example, the AI can link a file
   to the wrong USB drive. Lean then finds that the identifiers are different, and it refuses
   the claim.
4. **Verify.** A second checker, con-leche, checks each proof again.

The app shows the accepted findings in a summary, a timeline of events and a proof graph. The
proof graph connects each finding to its records and to the disk image. The app also makes a
forensic examination report. Investigators can examine and export this report.

## Open the app

```sh
git clone https://github.com/pauljiang03/conan && cd conan && ./install.sh
```

On a Mac, this command adds **Conan** to your Applications folder and opens it.
