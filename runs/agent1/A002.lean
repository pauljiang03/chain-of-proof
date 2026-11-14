import ChainOfProof
open ChainOfProof

namespace Cert.A002

def cited : List Fact := [
  ⟨2, .usbInsert, 1427204280014221, 1, 1, 0⟩ ]

def claim : Claim := Sets.usbConnected 2

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A002

#print axioms Cert.A002.verified
