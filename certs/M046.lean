import ChainOfProof
open ChainOfProof

namespace Cert.M046

def cited : List Fact := [
  ⟨300, .webSearch, 1427133922229486, 1, 166, 159⟩,
  ⟨480, .tag, 1794614400000000, 1, 166, 229⟩ ]

def claim : Claim := .both (Sets.searched 300) (Sets.tagged 300 .obj 480 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M046

#print axioms Cert.M046.verified
