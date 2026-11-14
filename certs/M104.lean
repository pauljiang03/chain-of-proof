import ChainOfProof
open ChainOfProof

namespace Cert.M104

def cited : List Fact := [
  ⟨90, .fileCreated, 1427144122950000, 10000, 74, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨315, .tag, 1794614400000000, 1, 2, 194⟩,
  ⟨142, .fileModified, 1358878760000000, 2000000, 74, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 90 376) (.both (Sets.deviceExamined 3 376) (.both (Sets.tagged 3 .obj 315 194) (Sets.copiedHere 90 142)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M104

#print axioms Cert.M104.verified
