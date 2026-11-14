import ChainOfProof
open ChainOfProof

namespace Cert.M227

def cited : List Fact := [
  ⟨385, .cdBurn, 1427229681619709, 1, 224, 219⟩ ]

def claim : Claim := Sets.burnTrace 385

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M227

#print axioms Cert.M227.verified
