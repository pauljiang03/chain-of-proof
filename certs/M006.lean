import ChainOfProof
open ChainOfProof

namespace Cert.M006

def cited : List Fact := [
  ⟨22, .lnkTarget, 1427135874491716, 1, 18, 19⟩,
  ⟨496, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩,
  ⟨405, .tag, 1794614400000000, 1, 18, 231⟩,
  ⟨406, .tag, 1794614400000000, 1, 18, 235⟩,
  ⟨1, .usbInsert, 1427135470593000, 1000, 1, 0⟩,
  ⟨388, .tag, 1794614400000000, 1, 1, 227⟩ ]

def claim : Claim := .both (Sets.openedFromDevice 22 496) (.both (Sets.tagged 22 .obj 405 231) (.both (Sets.tagged 22 .obj 406 235) (.both (Sets.deviceHolds 1 496) (Sets.tagged 1 .obj 388 227))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M006

#print axioms Cert.M006.verified
