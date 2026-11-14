import ChainOfProof
open ChainOfProof

namespace Cert.M226

def cited : List Fact := [
  ⟨384, .cdBurn, 1427228686429152, 1, 220, 221⟩ ]

def claim : Claim := Sets.burnTrace 384

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M226

#print axioms Cert.M226.verified
