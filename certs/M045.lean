import ChainOfProof
open ChainOfProof

namespace Cert.M045

def cited : List Fact := [
  ⟨225, .webSearch, 1427133919638342, 1, 132, 125⟩,
  ⟨358, .tag, 1794614400000000, 1, 132, 195⟩ ]

def claim : Claim := .both (Sets.searched 225) (Sets.tagged 225 .obj 358 195)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M045

#print axioms Cert.M045.verified
