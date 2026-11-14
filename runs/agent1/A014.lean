import ChainOfProof
open ChainOfProof

namespace Cert.A014

def cited : List Fact := [
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨242, .volumeOnDevice, 1794614400000000, 1, 2, 121⟩,
  ⟨238, .volumeSeen, 1427230954309607, 1, 120, 121⟩,
  ⟨199, .tag, 1794614400000000, 1, 2, 116⟩ ]

def claim : Claim := .both (Sets.deviceHolds 3 242) (.both (Sets.recordedOnDevice 238 242) (Sets.tagged 3 .obj 199 116))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A014

#print axioms Cert.A014.verified
