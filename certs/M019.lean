import ChainOfProof
open ChainOfProof

namespace Cert.M019

def cited : List Fact := [
  ⟨36, .lnkTarget, 1427142453267067, 1, 28, 26⟩,
  ⟨212, .tag, 1794614400000000, 1, 28, 118⟩ ]

def claim : Claim := .both (Sets.opened 36) (Sets.tagged 36 .obj 212 118)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M019

#print axioms Cert.M019.verified
