import ChainOfProof
open ChainOfProof

namespace Cert.M005

def cited : List Fact := [
  ⟨21, .lnkTarget, 1427135840499256, 1, 18, 19⟩,
  ⟨374, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩,
  ⟨331, .tag, 1794614400000000, 1, 18, 197⟩,
  ⟨332, .tag, 1794614400000000, 1, 18, 201⟩,
  ⟨1, .usbInsert, 1427135470593000, 1000, 1, 0⟩,
  ⟨314, .tag, 1794614400000000, 1, 1, 193⟩ ]

def claim : Claim := .both (Sets.openedFromDevice 21 374) (.both (Sets.tagged 21 .obj 331 197) (.both (Sets.tagged 21 .obj 332 201) (.both (Sets.deviceHolds 1 374) (Sets.tagged 1 .obj 314 193))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M005

#print axioms Cert.M005.verified
