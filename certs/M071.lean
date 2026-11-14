import ChainOfProof
open ChainOfProof

namespace Cert.M071

def cited : List Fact := [
  ⟨194, .webSearch, 1427294804752905, 1, 112, 70⟩,
  ⟨215, .tag, 1794614400000000, 1, 112, 117⟩ ]

def claim : Claim := .both (Sets.searched 194) (Sets.tagged 194 .obj 215 117)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M071

#print axioms Cert.M071.verified
