import ChainOfProof
open ChainOfProof

namespace Cert.A082

def cited : List Fact := [
  ⟨161, .fileCreated, 1427230620985995, 1, 42, 40⟩,
  ⟨50, .lnkTarget, 1427230870763657, 1, 23, 40⟩ ]

def claim : Claim := .before 161 50

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A082

#print axioms Cert.A082.verified
