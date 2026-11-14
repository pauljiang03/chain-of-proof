import ChainOfProof
open ChainOfProof

namespace Cert.A099

def cited : List Fact := [
  ⟨371, .volumeSeen, 1427230954309607, 1, 203, 205⟩,
  ⟨375, .volumeOnDevice, 1794614400000000, 1, 2, 205⟩,
  ⟨366, .volumeSeen, 1427205514439312, 1, 203, 31⟩ ]

def claim : Claim := .both (Sets.recordedOnDevice 371 375) (.both (Sets.sameLabel 366 371) (.before 366 371))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A099

#print axioms Cert.A099.verified
