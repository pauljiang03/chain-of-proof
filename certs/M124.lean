import ChainOfProof
open ChainOfProof

namespace Cert.M124

def cited : List Fact := [
  ⟨110, .fileCreated, 1427205579580000, 10000, 94, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨315, .tag, 1794614400000000, 1, 2, 194⟩,
  ⟨172, .fileModified, 1421435424000000, 2000000, 94, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 110 376) (.both (Sets.deviceExamined 3 376) (.both (Sets.tagged 3 .obj 315 194) (.both (.before 3 110) (Sets.copiedHere 110 172))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M124

#print axioms Cert.M124.verified
