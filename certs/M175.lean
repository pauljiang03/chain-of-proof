import ChainOfProof
open ChainOfProof

namespace Cert.M175

def cited : List Fact := [
  ⟨309, .cdBurn, 1427228659896305, 1, 189, 185⟩ ]

def claim : Claim := Sets.burnTrace 309

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M175

#print axioms Cert.M175.verified
