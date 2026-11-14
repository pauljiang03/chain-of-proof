import ChainOfProof
open ChainOfProof

namespace Cert.A105

def cited : List Fact := [
  ⟨248, .webSearch, 1427134544517540, 1, 147, 125⟩,
  ⟨351, .tag, 1794614400000000, 1, 147, 195⟩ ]

def claim : Claim := Sets.tagged 248 .obj 351 195

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A105

#print axioms Cert.A105.verified
