import ChainOfProof
open ChainOfProof

namespace Cert.M023

def cited : List Fact := [
  ⟨40, .lnkTarget, 1427142457263674, 1, 28, 26⟩,
  ⟨410, .tag, 1794614400000000, 1, 28, 231⟩ ]

def claim : Claim := .both (Sets.opened 40) (Sets.tagged 40 .obj 410 231)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M023

#print axioms Cert.M023.verified
