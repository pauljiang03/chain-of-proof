import ChainOfProof
open ChainOfProof

namespace Cert.M213

def cited : List Fact := [
  ⟨371, .emailSent, 1427138441000000, 1000000, 210, 206⟩ ]

def claim : Claim := Sets.emailed 371

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M213

#print axioms Cert.M213.verified
