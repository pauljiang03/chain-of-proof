import ChainOfProof
open ChainOfProof

namespace Cert.A117

def cited : List Fact := [
  ⟨37, .lnkTarget, 1427142453313868, 1, 29, 26⟩ ]

def claim : Claim := Sets.opened 37

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A117

#print axioms Cert.A117.verified
