import ChainOfProof
open ChainOfProof

namespace Cert.M056

def cited : List Fact := [
  ⟨318, .webSearch, 1427134417494371, 1, 178, 160⟩,
  ⟨468, .tag, 1794614400000000, 1, 178, 229⟩ ]

def claim : Claim := .both (Sets.searched 318) (Sets.tagged 318 .obj 468 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M056

#print axioms Cert.M056.verified
