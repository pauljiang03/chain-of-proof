import ChainOfProof
open ChainOfProof

namespace Cert.A103

def cited : List Fact := [
  ⟨368, .volumeSeen, 1427229853752619, 1, 204, 35⟩,
  ⟨369, .volumeSeen, 1427230050485174, 1, 204, 39⟩,
  ⟨370, .volumeSeen, 1427230870763657, 1, 204, 40⟩ ]

def claim : Claim := .both (Sets.sameLabel 368 369) (Sets.sameLabel 369 370)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A103

#print axioms Cert.A103.verified
