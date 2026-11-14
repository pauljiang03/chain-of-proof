import ChainOfProof
open ChainOfProof

namespace Cert.A092

def cited : List Fact := [
  ⟨368, .emailSent, 1427131767000000, 1000000, 205, 206⟩,
  ⟨291, .webSearch, 1427133729303892, 1, 164, 159⟩ ]

def claim : Claim := .before 368 291

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A092

#print axioms Cert.A092.verified
