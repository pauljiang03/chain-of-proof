import ChainOfProof
open ChainOfProof

namespace Cert.A009

def cited : List Fact := [
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨315, .tag, 1794614400000000, 1, 2, 194⟩ ]

def claim : Claim := .both (Sets.usbConnected 3) (Sets.tagged 3 .obj 315 194)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A009

#print axioms Cert.A009.verified
