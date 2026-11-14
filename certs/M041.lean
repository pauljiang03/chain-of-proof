import ChainOfProof
open ChainOfProof

namespace Cert.M041

def cited : List Fact := [
  ⟨295, .webSearch, 1427133820424839, 1, 166, 159⟩,
  ⟨480, .tag, 1794614400000000, 1, 166, 229⟩ ]

def claim : Claim := .both (Sets.searched 295) (Sets.tagged 295 .obj 480 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M041

#print axioms Cert.M041.verified
