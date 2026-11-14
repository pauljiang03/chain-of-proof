import ChainOfProof
open ChainOfProof

namespace Cert.A130

def cited : List Fact := [
  ⟨24, .lnkTarget, 1427135874522916, 1, 20, 19⟩,
  ⟨328, .tag, 1794614400000000, 1, 20, 197⟩ ]

def claim : Claim := Sets.tagged 24 .obj 328 197

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A130

#print axioms Cert.A130.verified
