import ChainOfProof
open ChainOfProof

namespace Cert.M054

def cited : List Fact := [
  ⟨316, .webSearch, 1427134355567263, 1, 176, 160⟩,
  ⟨485, .tag, 1794614400000000, 1, 176, 229⟩ ]

def claim : Claim := .both (Sets.searched 316) (Sets.tagged 316 .obj 485 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M054

#print axioms Cert.M054.verified
