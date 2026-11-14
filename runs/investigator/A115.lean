import ChainOfProof
open ChainOfProof

namespace Cert.A115

def cited : List Fact := [
  ⟨218, .webSearch, 1427133764343210, 1, 131, 125⟩,
  ⟨361, .tag, 1794614400000000, 1, 131, 195⟩ ]

def claim : Claim := Sets.tagged 218 .obj 361 195

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A115

#print axioms Cert.A115.verified
