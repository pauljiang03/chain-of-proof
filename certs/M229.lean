import ChainOfProof
open ChainOfProof

namespace Cert.M229

def cited : List Fact := [
  ⟨387, .cdBurn, 1427230396668583, 1, 225, 226⟩ ]

def claim : Claim := Sets.burnTrace 387

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M229

#print axioms Cert.M229.verified
