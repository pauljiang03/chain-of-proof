import ChainOfProof
open ChainOfProof

namespace Cert.M012

def cited : List Fact := [
  ⟨29, .lnkTarget, 1427135903414167, 1, 24, 19⟩,
  ⟨241, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩,
  ⟨202, .tag, 1794614400000000, 1, 24, 118⟩,
  ⟨1, .usbInsert, 1427135470593000, 1000, 1, 0⟩,
  ⟨198, .tag, 1794614400000000, 1, 1, 115⟩ ]

def claim : Claim := .both (Sets.openedFromDevice 29 241) (.both (Sets.tagged 29 .obj 202 118) (.both (Sets.deviceHolds 1 241) (Sets.tagged 1 .obj 198 115)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M012

#print axioms Cert.M012.verified
