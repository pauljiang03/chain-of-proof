import ChainOfProof
open ChainOfProof

namespace Cert.A196

def cited : List Fact := [
  ⟨21, .lnkTarget, 1427135840499256, 1, 18, 19⟩ ]

def claim : Claim := Sets.opened 21

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A196

#print axioms Cert.A196.verified
