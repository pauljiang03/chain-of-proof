import ChainOfProof
open ChainOfProof

namespace Cert.A116

def cited : List Fact := [
  ⟨36, .lnkTarget, 1427142453267067, 1, 28, 26⟩ ]

def claim : Claim := Sets.opened 36

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A116

#print axioms Cert.A116.verified
