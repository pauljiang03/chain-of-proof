import ChainOfProof
open ChainOfProof

namespace Cert.A083

def cited : List Fact := [
  ⟨302, .emailSent, 1427204110365000, 1000000, 181, 174⟩,
  ⟨124, .fileCreated, 1427205618410000, 10000, 108, 69⟩ ]

def claim : Claim := .before 302 124

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A083

#print axioms Cert.A083.verified
