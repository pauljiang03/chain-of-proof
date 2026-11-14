import ChainOfProof
open ChainOfProof

namespace Cert.A184

def cited : List Fact := [
  ⟨301, .emailSent, 1427203557000000, 1000000, 180, 172⟩,
  ⟨302, .emailSent, 1427204110365000, 1000000, 181, 174⟩ ]

def claim : Claim := .before 301 302

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A184

#print axioms Cert.A184.verified
