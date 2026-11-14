import ChainOfProof
open ChainOfProof

namespace Cert.M037

def cited : List Fact := [
  ⟨121, .webSearch, 1427133729303892, 1, 74, 69⟩,
  ⟨221, .tag, 1794614400000000, 1, 74, 117⟩ ]

def claim : Claim := .both (Sets.searched 121) (Sets.tagged 121 .obj 221 117)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M037

#print axioms Cert.M037.verified
