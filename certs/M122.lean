import ChainOfProof
open ChainOfProof

namespace Cert.M122

def cited : List Fact := [
  ⟨108, .fileCreated, 1427205567120000, 10000, 92, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨315, .tag, 1794614400000000, 1, 2, 194⟩,
  ⟨177, .fileModified, 1422046030000000, 2000000, 92, 69⟩,
  ⟨339, .tag, 1794614400000000, 1, 92, 199⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 108 376) (.both (Sets.deviceExamined 3 376) (.both (Sets.tagged 3 .obj 315 194) (.both (.before 3 108) (.both (Sets.copiedHere 108 177) (Sets.tagged 108 .obj 339 199)))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M122

#print axioms Cert.M122.verified
