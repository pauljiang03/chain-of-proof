import ChainOfProof
open ChainOfProof

namespace Cert.M225

def cited : List Fact := [
  ⟨383, .cdBurn, 1427228659896305, 1, 223, 219⟩ ]

def claim : Claim := Sets.burnTrace 383

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M225

#print axioms Cert.M225.verified
