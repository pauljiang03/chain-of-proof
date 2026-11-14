import ChainOfProof
open ChainOfProof

namespace Cert.A164

def cited : List Fact := [
  ⟨368, .volumeSeen, 1427229853752619, 1, 204, 35⟩,
  ⟨369, .volumeSeen, 1427230050485174, 1, 204, 39⟩ ]

def claim : Claim := Sets.sameLabel 368 369

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A164

#print axioms Cert.A164.verified
