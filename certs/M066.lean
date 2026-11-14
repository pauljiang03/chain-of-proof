import ChainOfProof
open ChainOfProof

namespace Cert.M066

def cited : List Fact := [
  ⟨159, .webSearch, 1427134726050680, 1, 95, 69⟩,
  ⟨229, .tag, 1794614400000000, 1, 95, 117⟩ ]

def claim : Claim := .both (Sets.searched 159) (Sets.tagged 159 .obj 229 117)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M066

#print axioms Cert.M066.verified
