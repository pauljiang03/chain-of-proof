import ChainOfProof
open ChainOfProof

namespace Cert.A135

def cited : List Fact := [
  ⟨49, .lnkTarget, 1427230050485174, 1, 23, 39⟩ ]

def claim : Claim := Sets.opened 49

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A135

#print axioms Cert.A135.verified
