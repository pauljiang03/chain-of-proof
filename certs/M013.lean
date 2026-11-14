import ChainOfProof
open ChainOfProof

namespace Cert.M013

def cited : List Fact := [
  ⟨30, .lnkTarget, 1427135903445366, 1, 22, 19⟩,
  ⟨496, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩,
  ⟨397, .tag, 1794614400000000, 1, 22, 231⟩,
  ⟨1, .usbInsert, 1427135470593000, 1000, 1, 0⟩,
  ⟨388, .tag, 1794614400000000, 1, 1, 227⟩ ]

def claim : Claim := .both (Sets.openedFromDevice 30 496) (.both (Sets.tagged 30 .obj 397 231) (.both (Sets.deviceHolds 1 496) (Sets.tagged 1 .obj 388 227)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M013

#print axioms Cert.M013.verified
