import ChainOfProof
open ChainOfProof

namespace Cert.M009

def cited : List Fact := [
  ⟨26, .lnkTarget, 1427135901167763, 1, 22, 19⟩,
  ⟨241, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩,
  ⟨203, .tag, 1794614400000000, 1, 22, 118⟩,
  ⟨1, .usbInsert, 1427135470593000, 1000, 1, 0⟩,
  ⟨198, .tag, 1794614400000000, 1, 1, 115⟩ ]

def claim : Claim := .both (Sets.openedFromDevice 26 241) (.both (Sets.tagged 26 .obj 203 118) (.both (Sets.deviceHolds 1 241) (Sets.tagged 1 .obj 198 115)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M009

#print axioms Cert.M009.verified
