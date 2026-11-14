import ChainOfProof
open ChainOfProof

namespace Cert.A095

def cited : List Fact := [
  ⟨236, .webSearch, 1427134111817280, 1, 137, 126⟩,
  ⟨316, .tag, 1794614400000000, 1, 137, 195⟩ ]

def claim : Claim := Sets.tagged 236 .obj 316 195

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A095

#print axioms Cert.A095.verified
