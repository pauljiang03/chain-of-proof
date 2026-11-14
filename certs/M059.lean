import ChainOfProof
open ChainOfProof

namespace Cert.M059

def cited : List Fact := [
  ⟨248, .webSearch, 1427134544517540, 1, 147, 125⟩,
  ⟨351, .tag, 1794614400000000, 1, 147, 195⟩ ]

def claim : Claim := .both (Sets.searched 248) (Sets.tagged 248 .obj 351 195)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M059

#print axioms Cert.M059.verified
