import ChainOfProof
open ChainOfProof

namespace Cert.A264

def cited : List Fact := [
  ⟨313, .cdBurn, 1427230396668583, 1, 191, 192⟩ ]

def claim : Claim := Sets.burnTrace 313

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A264

#print axioms Cert.A264.verified
