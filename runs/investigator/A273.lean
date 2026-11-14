import ChainOfProof
open ChainOfProof

namespace Cert.A273

def cited : List Fact := [
  ⟨2, .usbInsert, 1427204280014221, 1, 1, 0⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩ ]

def claim : Claim := .before 2 3

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A273

#print axioms Cert.A273.verified
