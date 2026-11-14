import ChainOfProof
open ChainOfProof

namespace Cert.M023

def cited : List Fact := [
  ⟨40, .lnkTarget, 1427142457263674, 1, 28, 26⟩,
  ⟨212, .tag, 1794614400000000, 1, 28, 118⟩ ]

def claim : Claim := .both (Sets.opened 40) (Sets.tagged 40 .obj 212 118)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M023

#print axioms Cert.M023.verified
