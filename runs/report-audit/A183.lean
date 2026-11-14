import ChainOfProof
open ChainOfProof

namespace Cert.A183

def cited : List Fact := [
  ⟨302, .emailSent, 1427204110365000, 1000000, 181, 174⟩ ]

def claim : Claim := Sets.emailed 302

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A183

#print axioms Cert.A183.verified
