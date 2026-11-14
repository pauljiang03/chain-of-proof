import ChainOfProof
open ChainOfProof

namespace Cert.M020

def cited : List Fact := [
  ⟨37, .lnkTarget, 1427142453313868, 1, 29, 26⟩,
  ⟨335, .tag, 1794614400000000, 1, 29, 197⟩ ]

def claim : Claim := .both (Sets.opened 37) (Sets.tagged 37 .obj 335 197)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M020

#print axioms Cert.M020.verified
