import ChainOfProof
open ChainOfProof

namespace Cert.A191

def cited : List Fact := [
  ⟨308, .cdBurn, 1427226971965935, 1, 186, 187⟩ ]

def claim : Claim := Sets.burnTrace 308

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A191

#print axioms Cert.A191.verified
