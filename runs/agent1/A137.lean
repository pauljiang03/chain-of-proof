import ChainOfProof
open ChainOfProof

namespace Cert.A137

def cited : List Fact := [
  ⟨51, .lnkTarget, 1427230870904057, 1, 41, 40⟩ ]

def claim : Claim := Sets.opened 51

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A137

#print axioms Cert.A137.verified
