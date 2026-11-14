import ChainOfProof
open ChainOfProof

namespace Cert.M124

def cited : List Fact := [
  ⟨110, .fileCreated, 1427205579580000, 10000, 94, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨389, .tag, 1794614400000000, 1, 2, 228⟩,
  ⟨238, .fileModified, 1421435424000000, 2000000, 94, 69⟩,
  ⟨415, .tag, 1794614400000000, 1, 94, 236⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 110 499) (.both (Sets.deviceExamined 3 499) (.both (Sets.tagged 3 .obj 389 228) (.both (.before 3 110) (.both (Sets.copiedHere 110 238) (Sets.tagged 110 .obj 415 236)))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M124

#print axioms Cert.M124.verified
