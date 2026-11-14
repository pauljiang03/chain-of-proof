import ChainOfProof
open ChainOfProof

namespace Cert.A150

def cited : List Fact := [
  ⟨121, .webSearch, 1427133729303892, 1, 74, 69⟩,
  ⟨221, .tag, 1794614400000000, 1, 74, 117⟩ ]

def claim : Claim := Sets.tagged 121 .obj 221 117

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A150

#print axioms Cert.A150.verified
