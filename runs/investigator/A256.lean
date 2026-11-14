import ChainOfProof
open ChainOfProof

namespace Cert.A256

def cited : List Fact := [
  ⟨305, .cdBurn, 1427226467407829, 1, 184, 185⟩ ]

def claim : Claim := Sets.burnTrace 305

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A256

#print axioms Cert.A256.verified
