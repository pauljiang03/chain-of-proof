import ChainOfProof
open ChainOfProof

namespace Cert.M057

def cited : List Fact := [
  ⟨246, .webSearch, 1427134451977428, 1, 145, 126⟩,
  ⟨354, .tag, 1794614400000000, 1, 145, 195⟩ ]

def claim : Claim := .both (Sets.searched 246) (Sets.tagged 246 .obj 354 195)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M057

#print axioms Cert.M057.verified
