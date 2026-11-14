import ChainOfProof
open ChainOfProof

namespace Cert.A067

def cited : List Fact := [
  ⟨193, .fileModified, 1427226708000000, 2000000, 109, 69⟩,
  ⟨371, .volumeSeen, 1427230954309607, 1, 203, 205⟩ ]

def claim : Claim := .before 193 371

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A067

#print axioms Cert.A067.verified
