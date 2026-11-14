import ChainOfProof
open ChainOfProof

namespace Cert.A280

def cited : List Fact := [
  ⟨371, .volumeSeen, 1427230954309607, 1, 203, 205⟩,
  ⟨304, .emailSent, 1427231109679000, 1000000, 183, 174⟩ ]

def claim : Claim := .before 371 304

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A280

#print axioms Cert.A280.verified
