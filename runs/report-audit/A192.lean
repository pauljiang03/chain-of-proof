import ChainOfProof
open ChainOfProof

namespace Cert.A192

def cited : List Fact := [
  ⟨309, .cdBurn, 1427228659896305, 1, 189, 185⟩ ]

def claim : Claim := Sets.burnTrace 309

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A192

#print axioms Cert.A192.verified
