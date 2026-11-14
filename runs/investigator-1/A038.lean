import ChainOfProof
open ChainOfProof

namespace Cert.A038

def cited : List Fact := [
  ⟨364, .webSearch, 1427294804752905, 1, 202, 160⟩,
  ⟨464, .tag, 1794614400000000, 1, 202, 229⟩,
  ⟨366, .webSearch, 1427294814471205, 1, 203, 160⟩,
  ⟨475, .tag, 1794614400000000, 1, 203, 229⟩,
  ⟨367, .webSearch, 1427294871248203, 1, 204, 160⟩,
  ⟨466, .tag, 1794614400000000, 1, 204, 229⟩ ]

def claim : Claim := .both (Sets.searched 364) (.both (Sets.tagged 364 .obj 464 229) (.both (Sets.searched 366) (.both (Sets.tagged 366 .obj 475 229) (.both (Sets.searched 367) (Sets.tagged 367 .obj 466 229)))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A038

#print axioms Cert.A038.verified
