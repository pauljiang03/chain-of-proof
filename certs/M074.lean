import ChainOfProof
open ChainOfProof

namespace Cert.M074

def cited : List Fact := [
  ⟨367, .webSearch, 1427294871248203, 1, 204, 160⟩,
  ⟨466, .tag, 1794614400000000, 1, 204, 229⟩ ]

def claim : Claim := .both (Sets.searched 367) (Sets.tagged 367 .obj 466 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M074

#print axioms Cert.M074.verified
