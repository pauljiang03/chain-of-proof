import ChainOfProof
open ChainOfProof

namespace Cert.A004

def cited : List Fact := [
  ⟨4, .usbInsert, 1427205513550110, 1, 2, 0⟩ ]

def claim : Claim := Sets.usbConnected 4

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A004

#print axioms Cert.A004.verified
