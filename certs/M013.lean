import ChainOfProof
open ChainOfProof

namespace Cert.M013

def cited : List Fact := [
  ⟨30, .lnkTarget, 1427135903445366, 1, 22, 19⟩,
  ⟨374, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩,
  ⟨323, .tag, 1794614400000000, 1, 22, 197⟩,
  ⟨1, .usbInsert, 1427135470593000, 1000, 1, 0⟩,
  ⟨314, .tag, 1794614400000000, 1, 1, 193⟩ ]

def claim : Claim := .both (Sets.openedFromDevice 30 374) (.both (Sets.tagged 30 .obj 323 197) (.both (Sets.deviceHolds 1 374) (Sets.tagged 1 .obj 314 193)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M013

#print axioms Cert.M013.verified
