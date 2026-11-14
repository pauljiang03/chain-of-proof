import ChainOfProof
open ChainOfProof

namespace Cert.A003

def cited : List Fact := [
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩ ]

def claim : Claim := Sets.usbConnected 3

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A003

#print axioms Cert.A003.verified
