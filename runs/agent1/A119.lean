import ChainOfProof
open ChainOfProof

namespace Cert.A119

def cited : List Fact := [
  ⟨39, .lnkTarget, 1427142453345068, 1, 28, 26⟩ ]

def claim : Claim := Sets.opened 39

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A119

#print axioms Cert.A119.verified
