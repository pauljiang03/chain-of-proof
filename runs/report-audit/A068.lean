import ChainOfProof
open ChainOfProof

namespace Cert.A068

def cited : List Fact := [
  ⟨126, .fileCreated, 1427226707220000, 10000, 109, 69⟩,
  ⟨371, .volumeSeen, 1427230954309607, 1, 203, 205⟩ ]

def claim : Claim := .before 126 371

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A068

#print axioms Cert.A068.verified
