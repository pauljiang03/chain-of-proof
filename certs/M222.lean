import ChainOfProof
open ChainOfProof

namespace Cert.M222

def cited : List Fact := [
  ⟨380, .cdBurn, 1427226467657431, 1, 220, 221⟩ ]

def claim : Claim := Sets.burnTrace 380

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M222

#print axioms Cert.M222.verified
