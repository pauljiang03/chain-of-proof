import ChainOfProof
open ChainOfProof

namespace Cert.M070

def cited : List Fact := [
  ⟨336, .webSearch, 1427143432477705, 1, 179, 160⟩,
  ⟨476, .tag, 1794614400000000, 1, 179, 229⟩ ]

def claim : Claim := .both (Sets.searched 336) (Sets.tagged 336 .obj 476 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M070

#print axioms Cert.M070.verified
