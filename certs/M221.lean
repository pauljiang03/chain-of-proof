import ChainOfProof
open ChainOfProof

namespace Cert.M221

def cited : List Fact := [
  ⟨379, .cdBurn, 1427226467407829, 1, 218, 219⟩ ]

def claim : Claim := Sets.burnTrace 379

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M221

#print axioms Cert.M221.verified
