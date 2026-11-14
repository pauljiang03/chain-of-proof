import ChainOfProof
open ChainOfProof

namespace Cert.A104

def cited : List Fact := [
  ⟨50, .lnkTarget, 1427230870763657, 1, 23, 40⟩,
  ⟨493, .volumeSeen, 1427230954309607, 1, 251, 253⟩ ]

def claim : Claim := .before 50 493

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A104

#print axioms Cert.A104.verified
