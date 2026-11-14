import ChainOfProof
open ChainOfProof

namespace Cert.A138

def cited : List Fact := [
  ⟨52, .lnkTarget, 1427230872900860, 1, 42, 40⟩ ]

def claim : Claim := Sets.opened 52

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A138

#print axioms Cert.A138.verified
