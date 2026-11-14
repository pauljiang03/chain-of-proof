import ChainOfProof
open ChainOfProof

namespace Cert.A114

def cited : List Fact := [
  ⟨34, .lnkTarget, 1427142414002193, 1, 27, 26⟩ ]

def claim : Claim := Sets.opened 34

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A114

#print axioms Cert.A114.verified
