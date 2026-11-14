import ChainOfProof
open ChainOfProof

namespace Cert.A194

def cited : List Fact := [
  ⟨311, .cdBurn, 1427229681619709, 1, 190, 185⟩ ]

def claim : Claim := Sets.burnTrace 311

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A194

#print axioms Cert.A194.verified
