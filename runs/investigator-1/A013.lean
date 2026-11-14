import ChainOfProof
open ChainOfProof

namespace Cert.A013

def cited : List Fact := [
  ⟨2, .usbInsert, 1427204280014221, 1, 1, 0⟩,
  ⟨4, .usbInsert, 1427205513550110, 1, 2, 0⟩ ]

def claim : Claim := .both (Sets.usbConnected 2) (Sets.usbConnected 4)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A013

#print axioms Cert.A013.verified
