import ChainOfProof
open ChainOfProof

namespace Cert.A129

def cited : List Fact := [
  ⟨26, .lnkTarget, 1427135901167763, 1, 22, 19⟩,
  ⟨323, .tag, 1794614400000000, 1, 22, 197⟩ ]

def claim : Claim := Sets.tagged 26 .obj 323 197

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A129

#print axioms Cert.A129.verified
