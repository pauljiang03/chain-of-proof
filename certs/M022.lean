import ChainOfProof
open ChainOfProof

namespace Cert.M022

def cited : List Fact := [
  ⟨39, .lnkTarget, 1427142453345068, 1, 28, 26⟩,
  ⟨212, .tag, 1794614400000000, 1, 28, 118⟩ ]

def claim : Claim := .both (Sets.opened 39) (Sets.tagged 39 .obj 212 118)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M022

#print axioms Cert.M022.verified
