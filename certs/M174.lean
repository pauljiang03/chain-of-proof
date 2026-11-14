import ChainOfProof
open ChainOfProof

namespace Cert.M174

def cited : List Fact := [
  ⟨308, .cdBurn, 1427226971965935, 1, 186, 187⟩ ]

def claim : Claim := Sets.burnTrace 308

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M174

#print axioms Cert.M174.verified
