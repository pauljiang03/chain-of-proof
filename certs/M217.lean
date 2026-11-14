import ChainOfProof
open ChainOfProof

namespace Cert.M217

def cited : List Fact := [
  ⟨375, .emailSent, 1427203557000000, 1000000, 214, 206⟩ ]

def claim : Claim := Sets.emailed 375

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M217

#print axioms Cert.M217.verified
