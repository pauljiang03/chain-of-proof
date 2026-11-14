import ChainOfProof
open ChainOfProof

namespace Cert.M046

def cited : List Fact := [
  ⟨226, .webSearch, 1427133922229486, 1, 132, 125⟩,
  ⟨358, .tag, 1794614400000000, 1, 132, 195⟩ ]

def claim : Claim := .both (Sets.searched 226) (Sets.tagged 226 .obj 358 195)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M046

#print axioms Cert.M046.verified
