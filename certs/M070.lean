import ChainOfProof
open ChainOfProof

namespace Cert.M070

def cited : List Fact := [
  ⟨262, .webSearch, 1427143432477705, 1, 145, 126⟩,
  ⟨354, .tag, 1794614400000000, 1, 145, 195⟩ ]

def claim : Claim := .both (Sets.searched 262) (Sets.tagged 262 .obj 354 195)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M070

#print axioms Cert.M070.verified
