# CONAN-F

**An AI forensic investigator. Lean 4 checks every finding.**

## Motivation

Digital forensic examiners must read very large disk images, and their findings go to court.
AI investigators can do this work fast, but they can state facts that the evidence does not
show. An examiner cannot use a finding that nobody can check.

## What we solve

CONAN-F gives examiners the speed of an AI investigator, and only findings that the evidence
proves. Each finding links to its records, its source on the disk image, and its proof.

## How we solve it

1. **Read.** Readers make records from the disk images.
2. **Investigate.** The AI investigator searches the records and proposes claims.
3. **Check.** The checker converts each claim to Lean code. The Lean kernel accepts a claim
   only when the cited records prove it.
4. **Verify.** A second checker, con-leche, checks each proof again.

The app and the report show only accepted findings, as a summary, a timeline and a proof graph.

## Open the app

```sh
git clone https://github.com/pauljiang03/conan && cd conan && ./install.sh
```

On a Mac, this adds **Conan** to your Applications folder and opens it.
