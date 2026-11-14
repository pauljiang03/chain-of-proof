import ChainOfProof
open ChainOfProof

namespace Cert.A176

def cited : List Fact := [
  ⟨297, .emailSent, 1427138441000000, 1000000, 176, 172⟩ ]

def claim : Claim := Sets.emailed 297

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A176

#print axioms Cert.A176.verified
