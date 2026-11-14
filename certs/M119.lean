import ChainOfProof
open ChainOfProof

namespace Cert.M119

def cited : List Fact := [
  ⟨105, .fileCreated, 1427144136610000, 10000, 89, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨315, .tag, 1794614400000000, 1, 2, 194⟩,
  ⟨152, .fileModified, 1367953870000000, 2000000, 89, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 105 376) (.both (Sets.deviceExamined 3 376) (.both (Sets.tagged 3 .obj 315 194) (Sets.copiedHere 105 152)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M119

#print axioms Cert.M119.verified
