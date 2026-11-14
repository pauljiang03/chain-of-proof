import ChainOfProof
open ChainOfProof

namespace Cert.M134

def cited : List Fact := [
  ⟨120, .fileCreated, 1427205612970000, 10000, 104, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨315, .tag, 1794614400000000, 1, 2, 194⟩,
  ⟨166, .fileModified, 1420485308000000, 2000000, 104, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 120 376) (.both (Sets.deviceExamined 3 376) (.both (Sets.tagged 3 .obj 315 194) (.both (.before 3 120) (Sets.copiedHere 120 166))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M134

#print axioms Cert.M134.verified
