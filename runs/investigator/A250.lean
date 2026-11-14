import ChainOfProof
open ChainOfProof

namespace Cert.A250

def cited : List Fact := [
  ⟨299, .emailSent, 1427138825282000, 1000000, 178, 174⟩ ]

def claim : Claim := Sets.emailed 299

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A250

#print axioms Cert.A250.verified
