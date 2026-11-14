import ChainOfProof
open ChainOfProof

namespace Cert.M055

def cited : List Fact := [
  ⟨317, .webSearch, 1427134400892344, 1, 177, 160⟩,
  ⟨467, .tag, 1794614400000000, 1, 177, 229⟩ ]

def claim : Claim := .both (Sets.searched 317) (Sets.tagged 317 .obj 467 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M055

#print axioms Cert.M055.verified
