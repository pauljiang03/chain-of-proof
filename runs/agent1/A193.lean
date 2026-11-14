import ChainOfProof
open ChainOfProof

namespace Cert.A193

def cited : List Fact := [
  ⟨197, .webSearch, 1427294871248203, 1, 114, 70⟩,
  ⟨55, .lnkTarget, 1427297289748404, 1, 44, 4⟩ ]

def claim : Claim := .before 197 55

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A193

#print axioms Cert.A193.verified
