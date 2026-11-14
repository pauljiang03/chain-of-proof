import ChainOfProof
open ChainOfProof

namespace Cert.A136

def cited : List Fact := [
  ⟨50, .lnkTarget, 1427230870763657, 1, 23, 40⟩ ]

def claim : Claim := Sets.opened 50

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A136

#print axioms Cert.A136.verified
