import ChainOfProof
open ChainOfProof

namespace Cert.M121

def cited : List Fact := [
  ⟨107, .fileCreated, 1427144137810000, 10000, 91, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨389, .tag, 1794614400000000, 1, 2, 228⟩,
  ⟨193, .fileModified, 1367953948000000, 2000000, 91, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 107 499) (.both (Sets.deviceExamined 3 499) (.both (Sets.tagged 3 .obj 389 228) (Sets.copiedHere 107 193)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M121

#print axioms Cert.M121.verified
