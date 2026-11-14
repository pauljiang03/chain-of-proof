import ChainOfProof
open ChainOfProof

namespace Cert.M024

def cited : List Fact := [
  ⟨41, .lnkTarget, 1427205683393024, 1, 30, 31⟩,
  ⟨366, .volumeSeen, 1427205514439312, 1, 203, 31⟩,
  ⟨333, .tag, 1794614400000000, 1, 30, 197⟩,
  ⟨371, .volumeSeen, 1427230954309607, 1, 203, 205⟩,
  ⟨375, .volumeOnDevice, 1794614400000000, 1, 2, 205⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨315, .tag, 1794614400000000, 1, 2, 194⟩ ]

def claim : Claim := .both (Sets.openedFromRecorded 41 366) (.both (Sets.tagged 41 .obj 333 197) (.both (Sets.sameLabel 366 371) (.both (Sets.recordedOnDevice 371 375) (.both (Sets.deviceHolds 3 375) (Sets.tagged 3 .obj 315 194)))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M024

#print axioms Cert.M024.verified
