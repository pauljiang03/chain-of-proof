import ChainOfProof
open ChainOfProof

namespace Cert.A145

def cited : List Fact := [
  ⟨55, .lnkTarget, 1427297289748404, 1, 44, 4⟩ ]

def claim : Claim := Sets.opened 55

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A145

#print axioms Cert.A145.verified
