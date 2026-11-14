import ChainOfProof
open ChainOfProof

namespace Cert.A142

def cited : List Fact := [
  ⟨34, .lnkTarget, 1427142414002193, 1, 27, 26⟩ ]

def claim : Claim := Sets.opened 34

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A142

#print axioms Cert.A142.verified
