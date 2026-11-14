import ChainOfProof
open ChainOfProof

namespace Cert.A040

def cited : List Fact := [
  ⟨42, .lnkTarget, 1427205689781835, 1, 32, 0⟩ ]

def claim : Claim := Sets.opened 42

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A040

#print axioms Cert.A040.verified
