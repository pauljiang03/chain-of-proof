import ChainOfProof
open ChainOfProof

namespace Cert.A016

def cited : List Fact := [
  ⟨1, .usbInsert, 1427135470593000, 1000, 1, 0⟩,
  ⟨496, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩,
  ⟨486, .volumeSeen, 1427135472853809, 1, 250, 19⟩,
  ⟨388, .tag, 1794614400000000, 1, 1, 227⟩ ]

def claim : Claim := .both (Sets.deviceHolds 1 496) (.both (Sets.recordedOnDevice 486 496) (Sets.tagged 1 .obj 388 227))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A016

#print axioms Cert.A016.verified
