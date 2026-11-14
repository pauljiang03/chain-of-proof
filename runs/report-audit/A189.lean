import ChainOfProof
open ChainOfProof

namespace Cert.A189

def cited : List Fact := [
  ⟨306, .cdBurn, 1427226467657431, 1, 186, 187⟩ ]

def claim : Claim := Sets.burnTrace 306

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A189

#print axioms Cert.A189.verified
