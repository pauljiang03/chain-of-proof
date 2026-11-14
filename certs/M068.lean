import ChainOfProof
open ChainOfProof

namespace Cert.M068

def cited : List Fact := [
  ⟨257, .webSearch, 1427140063009623, 1, 152, 125⟩,
  ⟨350, .tag, 1794614400000000, 1, 152, 195⟩ ]

def claim : Claim := .both (Sets.searched 257) (Sets.tagged 257 .obj 350 195)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M068

#print axioms Cert.M068.verified
