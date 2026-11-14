import ChainOfProof
open ChainOfProof

namespace Cert.A081

def cited : List Fact := [
  ⟨129, .fileCreated, 1427230482676152, 1, 34, 111⟩,
  ⟨161, .fileCreated, 1427230620985995, 1, 42, 40⟩ ]

def claim : Claim := .before 129 161

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A081

#print axioms Cert.A081.verified
