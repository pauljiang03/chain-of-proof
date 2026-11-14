import ChainOfProof
open ChainOfProof

namespace Cert.M123

def cited : List Fact := [
  ⟨109, .fileCreated, 1427205577630000, 10000, 93, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨315, .tag, 1794614400000000, 1, 2, 194⟩,
  ⟨160, .fileModified, 1418746226000000, 2000000, 93, 69⟩,
  ⟨340, .tag, 1794614400000000, 1, 93, 198⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 109 376) (.both (Sets.deviceExamined 3 376) (.both (Sets.tagged 3 .obj 315 194) (.both (.before 3 109) (.both (Sets.copiedHere 109 160) (Sets.tagged 109 .obj 340 198)))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M123

#print axioms Cert.M123.verified
