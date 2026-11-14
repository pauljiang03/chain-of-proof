import ChainOfProof
open ChainOfProof

namespace Cert.M037

def cited : List Fact := [
  ⟨291, .webSearch, 1427133729303892, 1, 164, 159⟩,
  ⟨470, .tag, 1794614400000000, 1, 164, 229⟩ ]

def claim : Claim := .both (Sets.searched 291) (Sets.tagged 291 .obj 470 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M037

#print axioms Cert.M037.verified
