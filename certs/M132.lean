import ChainOfProof
open ChainOfProof

namespace Cert.M132

def cited : List Fact := [
  ⟨118, .fileCreated, 1427205606780000, 10000, 102, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨315, .tag, 1794614400000000, 1, 2, 194⟩,
  ⟨164, .fileModified, 1419018826000000, 2000000, 102, 69⟩,
  ⟨342, .tag, 1794614400000000, 1, 102, 201⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 118 376) (.both (Sets.deviceExamined 3 376) (.both (Sets.tagged 3 .obj 315 194) (.both (.before 3 118) (.both (Sets.copiedHere 118 164) (Sets.tagged 118 .obj 342 201)))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M132

#print axioms Cert.M132.verified
