import ChainOfProof
open ChainOfProof

namespace Cert.A190

def cited : List Fact := [
  ⟨307, .cdBurn, 1427226961607515, 1, 188, 185⟩ ]

def claim : Claim := Sets.burnTrace 307

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A190

#print axioms Cert.A190.verified
