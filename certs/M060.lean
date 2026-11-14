import ChainOfProof
open ChainOfProof

namespace Cert.M060

def cited : List Fact := [
  ⟨249, .webSearch, 1427134615783075, 1, 148, 125⟩,
  ⟨355, .tag, 1794614400000000, 1, 148, 195⟩ ]

def claim : Claim := .both (Sets.searched 249) (Sets.tagged 249 .obj 355 195)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M060

#print axioms Cert.M060.verified
