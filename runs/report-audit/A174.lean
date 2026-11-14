import ChainOfProof
open ChainOfProof

namespace Cert.A174

def cited : List Fact := [
  ⟨294, .emailSent, 1427131767000000, 1000000, 171, 172⟩,
  ⟨295, .emailSent, 1427136271719000, 1000000, 173, 174⟩ ]

def claim : Claim := .before 294 295

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A174

#print axioms Cert.A174.verified
