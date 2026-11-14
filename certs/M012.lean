import ChainOfProof
open ChainOfProof

namespace Cert.M012

def cited : List Fact := [
  ⟨29, .lnkTarget, 1427135903414167, 1, 24, 19⟩,
  ⟨374, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩,
  ⟨322, .tag, 1794614400000000, 1, 24, 197⟩,
  ⟨1, .usbInsert, 1427135470593000, 1000, 1, 0⟩,
  ⟨314, .tag, 1794614400000000, 1, 1, 193⟩ ]

def claim : Claim := .both (Sets.openedFromDevice 29 374) (.both (Sets.tagged 29 .obj 322 197) (.both (Sets.deviceHolds 1 374) (Sets.tagged 1 .obj 314 193)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M012

#print axioms Cert.M012.verified
