import ChainOfProof
open ChainOfProof

namespace Cert.M043

def cited : List Fact := [
  ⟨127, .webSearch, 1427133915865196, 1, 76, 69⟩,
  ⟨230, .tag, 1794614400000000, 1, 76, 117⟩ ]

def claim : Claim := .both (Sets.searched 127) (Sets.tagged 127 .obj 230 117)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M043

#print axioms Cert.M043.verified
