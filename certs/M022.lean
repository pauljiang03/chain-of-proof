import ChainOfProof
open ChainOfProof

namespace Cert.M022

def cited : List Fact := [
  ⟨39, .lnkTarget, 1427142453345068, 1, 28, 26⟩,
  ⟨410, .tag, 1794614400000000, 1, 28, 231⟩ ]

def claim : Claim := .both (Sets.opened 39) (Sets.tagged 39 .obj 410 231)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M022

#print axioms Cert.M022.verified
