import ChainOfProof
open ChainOfProof

namespace Cert.M212

def cited : List Fact := [
  ⟨370, .emailSent, 1427138098000000, 1000000, 209, 206⟩ ]

def claim : Claim := Sets.emailed 370

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M212

#print axioms Cert.M212.verified
