import ChainOfProof
open ChainOfProof

namespace Cert.A101

def cited : List Fact := [
  ⟨244, .webSearch, 1427134417494371, 1, 144, 126⟩,
  ⟨347, .tag, 1794614400000000, 1, 144, 195⟩ ]

def claim : Claim := Sets.tagged 244 .obj 347 195

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A101

#print axioms Cert.A101.verified
