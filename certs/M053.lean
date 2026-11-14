import ChainOfProof
open ChainOfProof

namespace Cert.M053

def cited : List Fact := [
  ⟨145, .webSearch, 1427134310582693, 1, 85, 70⟩,
  ⟨232, .tag, 1794614400000000, 1, 85, 117⟩ ]

def claim : Claim := .both (Sets.searched 145) (Sets.tagged 145 .obj 232 117)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M053

#print axioms Cert.M053.verified
