import ChainOfProof
open ChainOfProof

namespace Cert.M138

def cited : List Fact := [
  ⟨124, .fileCreated, 1427205618410000, 10000, 108, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨315, .tag, 1794614400000000, 1, 2, 194⟩,
  ⟨174, .fileModified, 1421777886000000, 2000000, 108, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 124 376) (.both (Sets.deviceExamined 3 376) (.both (Sets.tagged 3 .obj 315 194) (.both (.before 3 124) (Sets.copiedHere 124 174))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M138

#print axioms Cert.M138.verified
