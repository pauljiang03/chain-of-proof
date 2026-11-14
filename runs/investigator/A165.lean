import ChainOfProof
open ChainOfProof

namespace Cert.A165

def cited : List Fact := [
  ⟨368, .volumeSeen, 1427229853752619, 1, 204, 35⟩,
  ⟨370, .volumeSeen, 1427230870763657, 1, 204, 40⟩ ]

def claim : Claim := Sets.sameLabel 368 370

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A165

#print axioms Cert.A165.verified
