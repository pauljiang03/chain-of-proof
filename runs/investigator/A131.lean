import ChainOfProof
open ChainOfProof

namespace Cert.A131

def cited : List Fact := [
  ⟨29, .lnkTarget, 1427135903414167, 1, 24, 19⟩,
  ⟨322, .tag, 1794614400000000, 1, 24, 197⟩ ]

def claim : Claim := Sets.tagged 29 .obj 322 197

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A131

#print axioms Cert.A131.verified
