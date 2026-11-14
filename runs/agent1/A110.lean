import ChainOfProof
open ChainOfProof

namespace Cert.A110

def cited : List Fact := [
  ⟨26, .lnkTarget, 1427135901167763, 1, 22, 19⟩,
  ⟨241, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩,
  ⟨1, .usbInsert, 1427135470593000, 1000, 1, 0⟩,
  ⟨203, .tag, 1794614400000000, 1, 22, 118⟩ ]

def claim : Claim := .both (Sets.openedFromDevice 26 241) (.both (Sets.deviceHolds 1 241) (Sets.tagged 26 .obj 203 118))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A110

#print axioms Cert.A110.verified
