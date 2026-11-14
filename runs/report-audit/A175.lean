import ChainOfProof
open ChainOfProof

namespace Cert.A175

def cited : List Fact := [
  ⟨296, .emailSent, 1427138098000000, 1000000, 175, 172⟩ ]

def claim : Claim := Sets.emailed 296

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A175

#print axioms Cert.A175.verified
