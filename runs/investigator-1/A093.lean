import ChainOfProof
open ChainOfProof

namespace Cert.A093

def cited : List Fact := [
  ⟨291, .webSearch, 1427133729303892, 1, 164, 159⟩,
  ⟨21, .lnkTarget, 1427135840499256, 1, 18, 19⟩ ]

def claim : Claim := .before 291 21

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A093

#print axioms Cert.A093.verified
