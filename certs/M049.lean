import ChainOfProof
open ChainOfProof

namespace Cert.M049

def cited : List Fact := [
  ⟨310, .webSearch, 1427134111817280, 1, 171, 160⟩,
  ⟨390, .tag, 1794614400000000, 1, 171, 229⟩ ]

def claim : Claim := .both (Sets.searched 310) (Sets.tagged 310 .obj 390 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M049

#print axioms Cert.M049.verified
