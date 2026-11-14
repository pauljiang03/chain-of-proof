import ChainOfProof
open ChainOfProof

namespace Cert.M223

def cited : List Fact := [
  ⟨381, .cdBurn, 1427226961607515, 1, 222, 219⟩ ]

def claim : Claim := Sets.burnTrace 381

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M223

#print axioms Cert.M223.verified
