### 0:00–0:20 | The hook
*Screen: CONAN-F, with the NIST case loaded.*

**We built Devin for digital forensics.**

Imagine handing an AI an entire criminal investigation and letting it work through the evidence on its own.

That's what we wanted to build. An AI forensic investigator that searches evidence, reconstructs events, and checks its own findings.

### 0:20–0:45 | The case
*Screen: Summary.*

Here's our test case from NIST.

A manager at a technology company is suspected of leaking confidential research to a competitor for money.

Security stops him with a USB drive and a CD, but finds no obvious evidence of the leak.

You're the investigator assigned to figure out what actually happened.

### 0:45–1:10 | The agent at work
*Screen: Timeline, then Proof Graph replay.*

We gave CONAN-F over 335,000 extracted forensic records from this case.

Our AI agent can search these records, investigate leads, and propose findings about the activity it discovers.

Here, we can see the timeline it reconstructed and replay how findings connect back to the original evidence.

### 1:10–1:40 | The technical breakthrough
*Screen: Show the Lean proof, ideally followed by the controlled incorrect USB claim.*

But there's a catch.

**AI can hallucinate, and a citation alone doesn't make a conclusion true.**

That's why we integrated Lean 4, a mathematical proof assistant.

Every proposed formal claim must pass our proof checker.

For example, if the AI links a file to the wrong USB drive, Lean detects that the identifiers don't match and refuses to certify the claim.

Supported claims receive independently verifiable proof certificates.

### 1:40–2:00 | The close
*Screen: Proof Graph with a verified finding selected.*

Think about what this means for investigators.

They can hand CONAN-F a case, let the agent work through thousands of records, and inspect the evidence behind its findings.

**We want AI to do the investigative legwork while making its conclusions independently checkable.**

That's CONAN-F.