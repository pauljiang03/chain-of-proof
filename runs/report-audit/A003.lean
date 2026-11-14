import ChainOfProof
open ChainOfProof

namespace Cert.A003

def cited : List Fact := [
  ⟨1, .usbInsert, 1427135470593000, 1000, 1, 0⟩,
  ⟨314, .tag, 1794614400000000, 1, 1, 193⟩ ]

def claim : Claim := .both (Sets.usbConnected 1) (Sets.tagged 1 .obj 314 193)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A003

#print axioms Cert.A003.verified
