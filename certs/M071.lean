import ChainOfProof
open ChainOfProof

namespace Cert.M071

def cited : List Fact := [
  ⟨364, .webSearch, 1427294804752905, 1, 202, 160⟩,
  ⟨464, .tag, 1794614400000000, 1, 202, 229⟩ ]

def claim : Claim := .both (Sets.searched 364) (Sets.tagged 364 .obj 464 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M071

#print axioms Cert.M071.verified
