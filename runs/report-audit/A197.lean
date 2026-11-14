import ChainOfProof
open ChainOfProof

namespace Cert.A197

def cited : List Fact := [
  ⟨217, .webSearch, 1427133729303892, 1, 130, 125⟩,
  ⟨349, .tag, 1794614400000000, 1, 130, 195⟩ ]

def claim : Claim := Sets.tagged 217 .obj 349 195

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A197

#print axioms Cert.A197.verified
