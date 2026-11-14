import ChainOfProof
open ChainOfProof

namespace Cert.A271

def cited : List Fact := [
  ⟨301, .emailSent, 1427203557000000, 1000000, 180, 172⟩,
  ⟨302, .emailSent, 1427204110365000, 1000000, 181, 174⟩ ]

def claim : Claim := .before 301 302

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A271

#print axioms Cert.A271.verified
