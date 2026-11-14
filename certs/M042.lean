import ChainOfProof
open ChainOfProof

namespace Cert.M042

def cited : List Fact := [
  ⟨222, .webSearch, 1427133873578434, 1, 132, 125⟩,
  ⟨358, .tag, 1794614400000000, 1, 132, 195⟩ ]

def claim : Claim := .both (Sets.searched 222) (Sets.tagged 222 .obj 358 195)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M042

#print axioms Cert.M042.verified
