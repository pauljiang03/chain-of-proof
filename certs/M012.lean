import ChainOfProof
open ChainOfProof

namespace Cert.M012

def cited : List Fact := [
  ⟨29, .lnkTarget, 1427135903414167, 1, 24, 19⟩,
  ⟨496, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩,
  ⟨396, .tag, 1794614400000000, 1, 24, 231⟩,
  ⟨1, .usbInsert, 1427135470593000, 1000, 1, 0⟩,
  ⟨388, .tag, 1794614400000000, 1, 1, 227⟩ ]

def claim : Claim := .both (Sets.openedFromDevice 29 496) (.both (Sets.tagged 29 .obj 396 231) (.both (Sets.deviceHolds 1 496) (Sets.tagged 1 .obj 388 227)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M012

#print axioms Cert.M012.verified
