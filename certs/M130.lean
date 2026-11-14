import ChainOfProof
open ChainOfProof

namespace Cert.M130

def cited : List Fact := [
  ⟨116, .fileCreated, 1427205584810000, 10000, 100, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨389, .tag, 1794614400000000, 1, 2, 228⟩,
  ⟨229, .fileModified, 1421087022000000, 2000000, 100, 69⟩,
  ⟨421, .tag, 1794614400000000, 1, 100, 242⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 116 499) (.both (Sets.deviceExamined 3 499) (.both (Sets.tagged 3 .obj 389 228) (.both (.before 3 116) (.both (Sets.copiedHere 116 229) (Sets.tagged 116 .obj 421 242)))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M130

#print axioms Cert.M130.verified
