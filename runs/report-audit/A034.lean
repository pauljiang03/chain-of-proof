import ChainOfProof
open ChainOfProof

namespace Cert.A034

def cited : List Fact := [
  ⟨35, .lnkTarget, 1427142416032196, 1, 25, 26⟩ ]

def claim : Claim := Sets.opened 35

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A034

#print axioms Cert.A034.verified
