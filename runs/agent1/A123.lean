import ChainOfProof
open ChainOfProof

namespace Cert.A123

def cited : List Fact := [
  ⟨41, .lnkTarget, 1427205683393024, 1, 30, 31⟩ ]

def claim : Claim := Sets.opened 41

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A123

#print axioms Cert.A123.verified
