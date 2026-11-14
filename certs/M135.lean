import ChainOfProof
open ChainOfProof

namespace Cert.M135

def cited : List Fact := [
  ⟨121, .fileCreated, 1427205613550000, 10000, 105, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨389, .tag, 1794614400000000, 1, 2, 228⟩,
  ⟨235, .fileModified, 1421097940000000, 2000000, 105, 69⟩,
  ⟨426, .tag, 1794614400000000, 1, 105, 245⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 121 499) (.both (Sets.deviceExamined 3 499) (.both (Sets.tagged 3 .obj 389 228) (.both (.before 3 121) (.both (Sets.copiedHere 121 235) (Sets.tagged 121 .obj 426 245)))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M135

#print axioms Cert.M135.verified
