import ChainOfProof
open ChainOfProof

namespace Cert.A166

def cited : List Fact := [
  ⟨369, .volumeSeen, 1427230050485174, 1, 204, 39⟩,
  ⟨370, .volumeSeen, 1427230870763657, 1, 204, 40⟩ ]

def claim : Claim := Sets.sameLabel 369 370

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A166

#print axioms Cert.A166.verified
