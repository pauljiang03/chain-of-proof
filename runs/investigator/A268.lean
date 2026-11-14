import ChainOfProof
open ChainOfProof

namespace Cert.A268

def cited : List Fact := [
  ⟨21, .lnkTarget, 1427135840499256, 1, 18, 19⟩,
  ⟨295, .emailSent, 1427136271719000, 1000000, 173, 174⟩ ]

def claim : Claim := .before 21 295

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A268

#print axioms Cert.A268.verified
