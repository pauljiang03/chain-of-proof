import ChainOfProof
open ChainOfProof

namespace Cert.A122

def cited : List Fact := [
  ⟨38, .lnkTarget, 1427142453345068, 1, 29, 26⟩ ]

def claim : Claim := Sets.opened 38

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A122

#print axioms Cert.A122.verified
