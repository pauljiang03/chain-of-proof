import ChainOfProof
open ChainOfProof

namespace Cert.A126

def cited : List Fact := [
  ⟨237, .volumeSeen, 1427205514439312, 1, 120, 31⟩,
  ⟨238, .volumeSeen, 1427230954309607, 1, 120, 121⟩ ]

def claim : Claim := Sets.sameLabel 237 238

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A126

#print axioms Cert.A126.verified
