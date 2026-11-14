import ChainOfProof
open ChainOfProof

namespace Cert.A190

def cited : List Fact := [
  ⟨54, .lnkTarget, 1427230874336063, 1, 23, 40⟩,
  ⟨238, .volumeSeen, 1427230954309607, 1, 120, 121⟩ ]

def claim : Claim := .before 54 238

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A190

#print axioms Cert.A190.verified
