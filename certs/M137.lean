import ChainOfProof
open ChainOfProof

namespace Cert.M137

def cited : List Fact := [
  ⟨123, .fileCreated, 1427205615650000, 10000, 107, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨389, .tag, 1794614400000000, 1, 2, 228⟩,
  ⟨247, .fileModified, 1421784300000000, 2000000, 107, 69⟩,
  ⟨428, .tag, 1794614400000000, 1, 107, 247⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 123 499) (.both (Sets.deviceExamined 3 499) (.both (Sets.tagged 3 .obj 389 228) (.both (.before 3 123) (.both (Sets.copiedHere 123 247) (Sets.tagged 123 .obj 428 247)))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M137

#print axioms Cert.M137.verified
