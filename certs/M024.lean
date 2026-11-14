import ChainOfProof
open ChainOfProof

namespace Cert.M024

def cited : List Fact := [
  ⟨41, .lnkTarget, 1427205683393024, 1, 30, 31⟩,
  ⟨237, .volumeSeen, 1427205514439312, 1, 120, 31⟩,
  ⟨209, .tag, 1794614400000000, 1, 30, 118⟩,
  ⟨238, .volumeSeen, 1427230954309607, 1, 120, 121⟩,
  ⟨242, .volumeOnDevice, 1794614400000000, 1, 2, 121⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨199, .tag, 1794614400000000, 1, 2, 116⟩ ]

def claim : Claim := .both (Sets.openedFromRecorded 41 237) (.both (Sets.tagged 41 .obj 209 118) (.both (Sets.sameLabel 237 238) (.both (Sets.recordedOnDevice 238 242) (.both (Sets.deviceHolds 3 242) (Sets.tagged 3 .obj 199 116)))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M024

#print axioms Cert.M024.verified
