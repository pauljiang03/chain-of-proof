import ChainOfProof
open ChainOfProof

namespace Cert.A097

def cited : List Fact := [
  ⟨4, .usbInsert, 1427205513550110, 1, 2, 0⟩,
  ⟨315, .tag, 1794614400000000, 1, 2, 194⟩ ]

def claim : Claim := .both (Sets.usbConnected 4) (Sets.tagged 4 .obj 315 194)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A097

#print axioms Cert.A097.verified
