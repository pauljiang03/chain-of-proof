import ChainOfProof
open ChainOfProof

namespace Cert.A137

def cited : List Fact := [
  ⟨41, .lnkTarget, 1427205683393024, 1, 30, 31⟩,
  ⟨333, .tag, 1794614400000000, 1, 30, 197⟩ ]

def claim : Claim := Sets.tagged 41 .obj 333 197

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A137

#print axioms Cert.A137.verified
