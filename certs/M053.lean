import ChainOfProof
open ChainOfProof

namespace Cert.M053

def cited : List Fact := [
  ⟨315, .webSearch, 1427134310582693, 1, 175, 160⟩,
  ⟨482, .tag, 1794614400000000, 1, 175, 229⟩ ]

def claim : Claim := .both (Sets.searched 315) (Sets.tagged 315 .obj 482 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M053

#print axioms Cert.M053.verified
