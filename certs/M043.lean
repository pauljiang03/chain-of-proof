import ChainOfProof
open ChainOfProof

namespace Cert.M043

def cited : List Fact := [
  ⟨223, .webSearch, 1427133915865196, 1, 132, 125⟩,
  ⟨358, .tag, 1794614400000000, 1, 132, 195⟩ ]

def claim : Claim := .both (Sets.searched 223) (Sets.tagged 223 .obj 358 195)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M043

#print axioms Cert.M043.verified
