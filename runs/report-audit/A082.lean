import ChainOfProof
open ChainOfProof

namespace Cert.A082

def cited : List Fact := [
  ⟨302, .emailSent, 1427204110365000, 1000000, 181, 174⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩ ]

def claim : Claim := .before 302 3

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A082

#print axioms Cert.A082.verified
