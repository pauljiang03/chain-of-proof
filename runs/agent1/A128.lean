import ChainOfProof
open ChainOfProof

namespace Cert.A128

def cited : List Fact := [
  ⟨41, .lnkTarget, 1427205683393024, 1, 30, 31⟩,
  ⟨209, .tag, 1794614400000000, 1, 30, 118⟩ ]

def claim : Claim := .both (Sets.opened 41) (Sets.tagged 41 .obj 209 118)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A128

#print axioms Cert.A128.verified
