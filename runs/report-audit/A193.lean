import ChainOfProof
open ChainOfProof

namespace Cert.A193

def cited : List Fact := [
  ⟨310, .cdBurn, 1427228686429152, 1, 186, 187⟩ ]

def claim : Claim := Sets.burnTrace 310

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A193

#print axioms Cert.A193.verified
