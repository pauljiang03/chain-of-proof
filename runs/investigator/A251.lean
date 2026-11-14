import ChainOfProof
open ChainOfProof

namespace Cert.A251

def cited : List Fact := [
  ⟨300, .emailSent, 1427143279000000, 1000000, 179, 172⟩ ]

def claim : Claim := Sets.emailed 300

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A251

#print axioms Cert.A251.verified
