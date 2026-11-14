import ChainOfProof
open ChainOfProof

namespace Cert.A125

def cited : List Fact := [
  ⟨125, .fileCreated, 1427222920734358, 1, 44, 4⟩,
  ⟨55, .lnkTarget, 1427297289748404, 1, 44, 4⟩ ]

def claim : Claim := .before 125 55

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A125

#print axioms Cert.A125.verified
