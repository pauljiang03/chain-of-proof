import ChainOfProof
open ChainOfProof

namespace Cert.A136

def cited : List Fact := [
  ⟨42, .lnkTarget, 1427205689781835, 1, 32, 0⟩ ]

def claim : Claim := Sets.opened 42

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A136

#print axioms Cert.A136.verified
