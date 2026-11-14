import ChainOfProof
open ChainOfProof

namespace Cert.M228

def cited : List Fact := [
  ⟨386, .cdBurn, 1427229681884909, 1, 220, 221⟩ ]

def claim : Claim := Sets.burnTrace 386

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M228

#print axioms Cert.M228.verified
