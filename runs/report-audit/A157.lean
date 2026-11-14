import ChainOfProof
open ChainOfProof

namespace Cert.A157

def cited : List Fact := [
  ⟨366, .volumeSeen, 1427205514439312, 1, 203, 31⟩,
  ⟨371, .volumeSeen, 1427230954309607, 1, 203, 205⟩ ]

def claim : Claim := .before 366 371

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A157

#print axioms Cert.A157.verified
