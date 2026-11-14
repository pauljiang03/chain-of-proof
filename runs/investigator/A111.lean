import ChainOfProof
open ChainOfProof

namespace Cert.A111

def cited : List Fact := [
  ⟨253, .webSearch, 1427134710872763, 1, 151, 125⟩,
  ⟨357, .tag, 1794614400000000, 1, 151, 195⟩ ]

def claim : Claim := Sets.tagged 253 .obj 357 195

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A111

#print axioms Cert.A111.verified
