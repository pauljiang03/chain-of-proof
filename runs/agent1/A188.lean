import ChainOfProof
open ChainOfProof

namespace Cert.A188

def cited : List Fact := [
  ⟨44, .lnkTarget, 1427229853752619, 1, 34, 35⟩,
  ⟨49, .lnkTarget, 1427230050485174, 1, 23, 39⟩ ]

def claim : Claim := .before 44 49

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A188

#print axioms Cert.A188.verified
