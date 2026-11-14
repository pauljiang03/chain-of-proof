import ChainOfProof
open ChainOfProof

namespace Cert.A191

def cited : List Fact := [
  ⟨238, .volumeSeen, 1427230954309607, 1, 120, 121⟩,
  ⟨193, .webSearch, 1427231210726427, 1, 111, 69⟩ ]

def claim : Claim := .before 238 193

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A191

#print axioms Cert.A191.verified
