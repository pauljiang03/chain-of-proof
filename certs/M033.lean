import ChainOfProof
open ChainOfProof

namespace Cert.M033

def cited : List Fact := [
  ⟨51, .lnkTarget, 1427230870904057, 1, 41, 40⟩ ]

def claim : Claim := Sets.opened 51

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M033

#print axioms Cert.M033.verified
