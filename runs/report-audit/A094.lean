import ChainOfProof
open ChainOfProof

namespace Cert.A094

def cited : List Fact := [
  ⟨1, .usbInsert, 1427135470593000, 1000, 1, 0⟩,
  ⟨374, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩,
  ⟨314, .tag, 1794614400000000, 1, 1, 193⟩ ]

def claim : Claim := .both (Sets.deviceHolds 1 374) (Sets.tagged 1 .obj 314 193)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A094

#print axioms Cert.A094.verified
