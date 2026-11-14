import ChainOfProof
open ChainOfProof

namespace Cert.A105

def cited : List Fact := [
  ⟨493, .volumeSeen, 1427230954309607, 1, 251, 253⟩,
  ⟨378, .emailSent, 1427231109679000, 1000000, 217, 208⟩ ]

def claim : Claim := .before 493 378

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A105

#print axioms Cert.A105.verified
