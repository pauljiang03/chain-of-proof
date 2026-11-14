import ChainOfProof
open ChainOfProof

namespace Cert.M070

def cited : List Fact := [
  ⟨166, .webSearch, 1427143432477705, 1, 89, 70⟩,
  ⟨226, .tag, 1794614400000000, 1, 89, 117⟩ ]

def claim : Claim := .both (Sets.searched 166) (Sets.tagged 166 .obj 226 117)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M070

#print axioms Cert.M070.verified
