import ChainOfProof
open ChainOfProof

namespace Cert.M114

def cited : List Fact := [
  ⟨100, .fileCreated, 1427144133200000, 10000, 84, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨315, .tag, 1794614400000000, 1, 2, 194⟩,
  ⟨146, .fileModified, 1358879424000000, 2000000, 84, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 100 376) (.both (Sets.deviceExamined 3 376) (.both (Sets.tagged 3 .obj 315 194) (Sets.copiedHere 100 146)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M114

#print axioms Cert.M114.verified
