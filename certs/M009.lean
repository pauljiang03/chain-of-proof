import ChainOfProof
open ChainOfProof

namespace Cert.M009

def cited : List Fact := [
  ⟨26, .lnkTarget, 1427135901167763, 1, 22, 19⟩,
  ⟨374, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩,
  ⟨323, .tag, 1794614400000000, 1, 22, 197⟩,
  ⟨1, .usbInsert, 1427135470593000, 1000, 1, 0⟩,
  ⟨314, .tag, 1794614400000000, 1, 1, 193⟩ ]

def claim : Claim := .both (Sets.openedFromDevice 26 374) (.both (Sets.tagged 26 .obj 323 197) (.both (Sets.deviceHolds 1 374) (Sets.tagged 1 .obj 314 193)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M009

#print axioms Cert.M009.verified
