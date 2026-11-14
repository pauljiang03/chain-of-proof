import ChainOfProof
open ChainOfProof

namespace Cert.M172

def cited : List Fact := [
  ⟨306, .cdBurn, 1427226467657431, 1, 186, 187⟩ ]

def claim : Claim := Sets.burnTrace 306

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M172

#print axioms Cert.M172.verified
