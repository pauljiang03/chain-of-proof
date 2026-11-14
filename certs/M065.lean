import ChainOfProof
open ChainOfProof

namespace Cert.M065

def cited : List Fact := [
  ⟨158, .webSearch, 1427134723263901, 1, 95, 69⟩,
  ⟨229, .tag, 1794614400000000, 1, 95, 117⟩ ]

def claim : Claim := .both (Sets.searched 158) (Sets.tagged 158 .obj 229 117)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M065

#print axioms Cert.M065.verified
