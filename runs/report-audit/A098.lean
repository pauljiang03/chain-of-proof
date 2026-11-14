import ChainOfProof
open ChainOfProof

namespace Cert.A098

def cited : List Fact := [
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨366, .volumeSeen, 1427205514439312, 1, 203, 31⟩,
  ⟨371, .volumeSeen, 1427230954309607, 1, 203, 205⟩,
  ⟨375, .volumeOnDevice, 1794614400000000, 1, 2, 205⟩ ]

def claim : Claim := .both (.before 3 366) (.both (Sets.sameLabel 366 371) (Sets.recordedOnDevice 371 375))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A098

#print axioms Cert.A098.verified
