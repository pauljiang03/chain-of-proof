import ChainOfProof
open ChainOfProof

namespace Cert.M055

def cited : List Fact := [
  ⟨243, .webSearch, 1427134400892344, 1, 143, 126⟩,
  ⟨346, .tag, 1794614400000000, 1, 143, 195⟩ ]

def claim : Claim := .both (Sets.searched 243) (Sets.tagged 243 .obj 346 195)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M055

#print axioms Cert.M055.verified
