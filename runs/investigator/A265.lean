import ChainOfProof
open ChainOfProof

namespace Cert.A265

def cited : List Fact := [
  ⟨294, .emailSent, 1427131767000000, 1000000, 171, 172⟩,
  ⟨217, .webSearch, 1427133729303892, 1, 130, 125⟩ ]

def claim : Claim := .before 294 217

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A265

#print axioms Cert.A265.verified
