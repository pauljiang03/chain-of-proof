import ChainOfProof
open ChainOfProof

namespace Cert.A081

def cited : List Fact := [
  ⟨294, .emailSent, 1427131767000000, 1000000, 171, 172⟩,
  ⟨21, .lnkTarget, 1427135840499256, 1, 18, 19⟩ ]

def claim : Claim := .before 294 21

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A081

#print axioms Cert.A081.verified
