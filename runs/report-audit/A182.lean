import ChainOfProof
open ChainOfProof

namespace Cert.A182

def cited : List Fact := [
  ⟨301, .emailSent, 1427203557000000, 1000000, 180, 172⟩ ]

def claim : Claim := Sets.emailed 301

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A182

#print axioms Cert.A182.verified
