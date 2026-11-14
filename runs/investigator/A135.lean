import ChainOfProof
open ChainOfProof

namespace Cert.A135

def cited : List Fact := [
  ⟨41, .lnkTarget, 1427205683393024, 1, 30, 31⟩,
  ⟨366, .volumeSeen, 1427205514439312, 1, 203, 31⟩,
  ⟨371, .volumeSeen, 1427230954309607, 1, 203, 205⟩,
  ⟨375, .volumeOnDevice, 1794614400000000, 1, 2, 205⟩ ]

def claim : Claim := .both (Sets.openedFromRecorded 41 366) (.both (Sets.sameLabel 366 371) (Sets.recordedOnDevice 371 375))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A135

#print axioms Cert.A135.verified
