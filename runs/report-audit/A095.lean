import ChainOfProof
open ChainOfProof

namespace Cert.A095

def cited : List Fact := [
  ⟨2, .usbInsert, 1427204280014221, 1, 1, 0⟩,
  ⟨374, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩,
  ⟨1, .usbInsert, 1427135470593000, 1000, 1, 0⟩ ]

def claim : Claim := .both (Sets.deviceHolds 2 374) (.before 1 2)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A095

#print axioms Cert.A095.verified
