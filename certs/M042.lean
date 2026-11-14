import ChainOfProof
open ChainOfProof

namespace Cert.M042

def cited : List Fact := [
  ⟨126, .webSearch, 1427133873578434, 1, 76, 69⟩,
  ⟨230, .tag, 1794614400000000, 1, 76, 117⟩ ]

def claim : Claim := .both (Sets.searched 126) (Sets.tagged 126 .obj 230 117)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M042

#print axioms Cert.M042.verified
