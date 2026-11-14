import ChainOfProof
open ChainOfProof

namespace Cert.M121

def cited : List Fact := [
  ⟨107, .fileCreated, 1427144137810000, 10000, 91, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨315, .tag, 1794614400000000, 1, 2, 194⟩,
  ⟨153, .fileModified, 1367953948000000, 2000000, 91, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 107 376) (.both (Sets.deviceExamined 3 376) (.both (Sets.tagged 3 .obj 315 194) (Sets.copiedHere 107 153)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M121

#print axioms Cert.M121.verified
