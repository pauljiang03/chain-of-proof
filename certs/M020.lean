import ChainOfProof
open ChainOfProof

namespace Cert.M020

def cited : List Fact := [
  ⟨37, .lnkTarget, 1427142453313868, 1, 29, 26⟩,
  ⟨409, .tag, 1794614400000000, 1, 29, 231⟩ ]

def claim : Claim := .both (Sets.opened 37) (Sets.tagged 37 .obj 409 231)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M020

#print axioms Cert.M020.verified
