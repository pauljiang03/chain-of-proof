import ChainOfProof
open ChainOfProof

namespace Cert.M126

def cited : List Fact := [
  ⟨112, .fileCreated, 1427205579710000, 10000, 96, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨315, .tag, 1794614400000000, 1, 2, 194⟩,
  ⟨156, .fileModified, 1417459826000000, 2000000, 96, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 112 376) (.both (Sets.deviceExamined 3 376) (.both (Sets.tagged 3 .obj 315 194) (.both (.before 3 112) (Sets.copiedHere 112 156))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M126

#print axioms Cert.M126.verified
