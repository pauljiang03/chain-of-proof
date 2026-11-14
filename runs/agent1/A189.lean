import ChainOfProof
open ChainOfProof

namespace Cert.A189

def cited : List Fact := [
  ⟨49, .lnkTarget, 1427230050485174, 1, 23, 39⟩,
  ⟨50, .lnkTarget, 1427230870763657, 1, 23, 40⟩ ]

def claim : Claim := .before 49 50

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A189

#print axioms Cert.A189.verified
