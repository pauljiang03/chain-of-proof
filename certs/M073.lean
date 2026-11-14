import ChainOfProof
open ChainOfProof

namespace Cert.M073

def cited : List Fact := [
  ⟨292, .webSearch, 1427294814471205, 1, 169, 126⟩,
  ⟨353, .tag, 1794614400000000, 1, 169, 195⟩ ]

def claim : Claim := .both (Sets.searched 292) (Sets.tagged 292 .obj 353 195)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M073

#print axioms Cert.M073.verified
