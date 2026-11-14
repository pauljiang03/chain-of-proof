import ChainOfProof
open ChainOfProof

namespace Cert.A262

def cited : List Fact := [
  ⟨311, .cdBurn, 1427229681619709, 1, 190, 185⟩ ]

def claim : Claim := Sets.burnTrace 311

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A262

#print axioms Cert.A262.verified
