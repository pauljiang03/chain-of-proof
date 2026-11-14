import ChainOfProof
open ChainOfProof

namespace Cert.A008

def cited : List Fact := [
  ⟨1, .usbInsert, 1427135470593000, 1000, 1, 0⟩,
  ⟨2, .usbInsert, 1427204280014221, 1, 1, 0⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨4, .usbInsert, 1427205513550110, 1, 2, 0⟩ ]

def census : Census := .distinct .usbInsert .obj 2

theorem verified : counts cited census = true := by decide +kernel

end Cert.A008

#print axioms Cert.A008.verified
