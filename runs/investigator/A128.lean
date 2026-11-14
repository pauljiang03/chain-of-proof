import ChainOfProof
open ChainOfProof

namespace Cert.A128

def cited : List Fact := [
  ⟨21, .lnkTarget, 1427135840499256, 1, 18, 19⟩,
  ⟨331, .tag, 1794614400000000, 1, 18, 197⟩ ]

def claim : Claim := Sets.tagged 21 .obj 331 197

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A128

#print axioms Cert.A128.verified
