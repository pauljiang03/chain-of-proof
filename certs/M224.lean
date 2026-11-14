import ChainOfProof
open ChainOfProof

namespace Cert.M224

def cited : List Fact := [
  ⟨382, .cdBurn, 1427226971965935, 1, 220, 221⟩ ]

def claim : Claim := Sets.burnTrace 382

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M224

#print axioms Cert.M224.verified
