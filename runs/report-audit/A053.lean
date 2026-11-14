import ChainOfProof
open ChainOfProof

namespace Cert.A053

def cited : List Fact := [
  ⟨55, .lnkTarget, 1427297289748404, 1, 44, 4⟩,
  ⟨127, .fileCreated, 1427297313647604, 1, 45, 4⟩ ]

def claim : Claim := .before 55 127

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A053

#print axioms Cert.A053.verified
