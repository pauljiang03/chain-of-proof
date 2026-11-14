import ChainOfProof
open ChainOfProof

namespace Cert.A150

def cited : List Fact := [
  ⟨36, .lnkTarget, 1427142453267067, 1, 28, 26⟩,
  ⟨336, .tag, 1794614400000000, 1, 28, 197⟩ ]

def claim : Claim := Sets.tagged 36 .obj 336 197

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A150

#print axioms Cert.A150.verified
