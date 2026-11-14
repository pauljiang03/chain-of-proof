import ChainOfProof
open ChainOfProof

namespace Cert.M176

def cited : List Fact := [
  ⟨310, .cdBurn, 1427228686429152, 1, 186, 187⟩ ]

def claim : Claim := Sets.burnTrace 310

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M176

#print axioms Cert.M176.verified
