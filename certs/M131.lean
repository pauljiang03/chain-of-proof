import ChainOfProof
open ChainOfProof

namespace Cert.M131

def cited : List Fact := [
  ⟨117, .fileCreated, 1427205584860000, 10000, 101, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨315, .tag, 1794614400000000, 1, 2, 194⟩,
  ⟨162, .fileModified, 1418939458000000, 2000000, 101, 69⟩,
  ⟨341, .tag, 1794614400000000, 1, 101, 200⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 117 376) (.both (Sets.deviceExamined 3 376) (.both (Sets.tagged 3 .obj 315 194) (.both (.before 3 117) (.both (Sets.copiedHere 117 162) (Sets.tagged 117 .obj 341 200)))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M131

#print axioms Cert.M131.verified
