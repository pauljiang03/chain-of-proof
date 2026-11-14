import ChainOfProof
open ChainOfProof

namespace Cert.M061

def cited : List Fact := [
  ⟨154, .webSearch, 1427134634631105, 1, 93, 69⟩,
  ⟨216, .tag, 1794614400000000, 1, 93, 117⟩ ]

def claim : Claim := .both (Sets.searched 154) (Sets.tagged 154 .obj 216 117)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M061

#print axioms Cert.M061.verified
