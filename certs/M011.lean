import ChainOfProof
open ChainOfProof

namespace Cert.M011

def cited : List Fact := [
  ⟨28, .lnkTarget, 1427135901230162, 1, 22, 19⟩,
  ⟨496, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩,
  ⟨397, .tag, 1794614400000000, 1, 22, 231⟩,
  ⟨1, .usbInsert, 1427135470593000, 1000, 1, 0⟩,
  ⟨388, .tag, 1794614400000000, 1, 1, 227⟩ ]

def claim : Claim := .both (Sets.openedFromDevice 28 496) (.both (Sets.tagged 28 .obj 397 231) (.both (Sets.deviceHolds 1 496) (Sets.tagged 1 .obj 388 227)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M011

#print axioms Cert.M011.verified
