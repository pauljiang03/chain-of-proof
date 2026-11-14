import ChainOfProof
open ChainOfProof

namespace Cert.M008

def cited : List Fact := [
  ⟨24, .lnkTarget, 1427135874522916, 1, 20, 19⟩,
  ⟨374, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩,
  ⟨328, .tag, 1794614400000000, 1, 20, 197⟩,
  ⟨1, .usbInsert, 1427135470593000, 1000, 1, 0⟩,
  ⟨314, .tag, 1794614400000000, 1, 1, 193⟩ ]

def claim : Claim := .both (Sets.openedFromDevice 24 374) (.both (Sets.tagged 24 .obj 328 197) (.both (Sets.deviceHolds 1 374) (Sets.tagged 1 .obj 314 193)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M008

#print axioms Cert.M008.verified
