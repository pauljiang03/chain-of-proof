import ChainOfProof
open ChainOfProof

namespace Cert.M046

def cited : List Fact := [
  ⟨130, .webSearch, 1427133922229486, 1, 76, 69⟩,
  ⟨230, .tag, 1794614400000000, 1, 76, 117⟩ ]

def claim : Claim := .both (Sets.searched 130) (Sets.tagged 130 .obj 230 117)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M046

#print axioms Cert.M046.verified
