import ChainOfProof
open ChainOfProof

namespace Cert.A109

def cited : List Fact := [
  ⟨21, .lnkTarget, 1427135840499256, 1, 18, 19⟩,
  ⟨241, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩,
  ⟨1, .usbInsert, 1427135470593000, 1000, 1, 0⟩,
  ⟨208, .tag, 1794614400000000, 1, 18, 118⟩ ]

def claim : Claim := .both (Sets.openedFromDevice 21 241) (.both (Sets.deviceHolds 1 241) (Sets.tagged 21 .obj 208 118))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A109

#print axioms Cert.A109.verified
