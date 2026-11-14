import ChainOfProof
open ChainOfProof

namespace Cert.M068

def cited : List Fact := [
  ⟨161, .webSearch, 1427140063009623, 1, 96, 69⟩,
  ⟨222, .tag, 1794614400000000, 1, 96, 117⟩ ]

def claim : Claim := .both (Sets.searched 161) (Sets.tagged 161 .obj 222 117)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M068

#print axioms Cert.M068.verified
