import ChainOfProof
open ChainOfProof

namespace Cert.M130

def cited : List Fact := [
  ⟨116, .fileCreated, 1427205584810000, 10000, 100, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨315, .tag, 1794614400000000, 1, 2, 194⟩,
  ⟨169, .fileModified, 1421087022000000, 2000000, 100, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 116 376) (.both (Sets.deviceExamined 3 376) (.both (Sets.tagged 3 .obj 315 194) (.both (.before 3 116) (Sets.copiedHere 116 169))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M130

#print axioms Cert.M130.verified
