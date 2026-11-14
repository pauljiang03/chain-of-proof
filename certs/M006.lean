import ChainOfProof
open ChainOfProof

namespace Cert.M006

def cited : List Fact := [
  ⟨22, .lnkTarget, 1427135874491716, 1, 18, 19⟩,
  ⟨241, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩,
  ⟨208, .tag, 1794614400000000, 1, 18, 118⟩,
  ⟨1, .usbInsert, 1427135470593000, 1000, 1, 0⟩,
  ⟨198, .tag, 1794614400000000, 1, 1, 115⟩ ]

def claim : Claim := .both (Sets.openedFromDevice 22 241) (.both (Sets.tagged 22 .obj 208 118) (.both (Sets.deviceHolds 1 241) (Sets.tagged 1 .obj 198 115)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M006

#print axioms Cert.M006.verified
