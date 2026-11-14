import ChainOfProof
open ChainOfProof

namespace Cert.A024

def cited : List Fact := [
  ⟨488, .volumeSeen, 1427205514439312, 1, 251, 31⟩,
  ⟨493, .volumeSeen, 1427230954309607, 1, 251, 253⟩ ]

def claim : Claim := .before 488 493

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A024

#print axioms Cert.A024.verified
