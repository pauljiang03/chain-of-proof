import ChainOfProof
open ChainOfProof

namespace Cert.M008

def cited : List Fact := [
  ⟨24, .lnkTarget, 1427135874522916, 1, 20, 19⟩,
  ⟨496, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩,
  ⟨402, .tag, 1794614400000000, 1, 20, 231⟩,
  ⟨1, .usbInsert, 1427135470593000, 1000, 1, 0⟩,
  ⟨388, .tag, 1794614400000000, 1, 1, 227⟩ ]

def claim : Claim := .both (Sets.openedFromDevice 24 496) (.both (Sets.tagged 24 .obj 402 231) (.both (Sets.deviceHolds 1 496) (Sets.tagged 1 .obj 388 227)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M008

#print axioms Cert.M008.verified
