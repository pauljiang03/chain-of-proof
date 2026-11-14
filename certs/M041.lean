import ChainOfProof
open ChainOfProof

namespace Cert.M041

def cited : List Fact := [
  ⟨125, .webSearch, 1427133820424839, 1, 76, 69⟩,
  ⟨230, .tag, 1794614400000000, 1, 76, 117⟩ ]

def claim : Claim := .both (Sets.searched 125) (Sets.tagged 125 .obj 230 117)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M041

#print axioms Cert.M041.verified
