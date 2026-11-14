import ChainOfProof
open ChainOfProof

namespace Cert.M137

def cited : List Fact := [
  ⟨123, .fileCreated, 1427205615650000, 10000, 107, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨315, .tag, 1794614400000000, 1, 2, 194⟩,
  ⟨175, .fileModified, 1421784300000000, 2000000, 107, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 123 376) (.both (Sets.deviceExamined 3 376) (.both (Sets.tagged 3 .obj 315 194) (.both (.before 3 123) (Sets.copiedHere 123 175))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M137

#print axioms Cert.M137.verified
