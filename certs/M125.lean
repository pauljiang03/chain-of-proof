import ChainOfProof
open ChainOfProof

namespace Cert.M125

def cited : List Fact := [
  ⟨111, .fileCreated, 1427205579680000, 10000, 95, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨315, .tag, 1794614400000000, 1, 2, 194⟩,
  ⟨168, .fileModified, 1420751304000000, 2000000, 95, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 111 376) (.both (Sets.deviceExamined 3 376) (.both (Sets.tagged 3 .obj 315 194) (.both (.before 3 111) (Sets.copiedHere 111 168))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M125

#print axioms Cert.M125.verified
