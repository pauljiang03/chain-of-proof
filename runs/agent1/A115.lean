import ChainOfProof
open ChainOfProof

namespace Cert.A115

def cited : List Fact := [
  ⟨35, .lnkTarget, 1427142416032196, 1, 25, 26⟩ ]

def claim : Claim := Sets.opened 35

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A115

#print axioms Cert.A115.verified
