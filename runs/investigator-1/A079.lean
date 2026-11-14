import ChainOfProof
open ChainOfProof

namespace Cert.A079

def cited : List Fact := [
  ⟨490, .volumeSeen, 1427229853752619, 1, 252, 35⟩,
  ⟨492, .volumeSeen, 1427230870763657, 1, 252, 40⟩,
  ⟨491, .volumeSeen, 1427230050485174, 1, 252, 39⟩ ]

def claim : Claim := .both (Sets.sameLabel 490 492) (Sets.sameLabel 491 492)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A079

#print axioms Cert.A079.verified
