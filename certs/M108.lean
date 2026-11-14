import ChainOfProof
open ChainOfProof

namespace Cert.M108

def cited : List Fact := [
  ⟨94, .fileCreated, 1427144127900000, 10000, 78, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨389, .tag, 1794614400000000, 1, 2, 228⟩,
  ⟨185, .fileModified, 1358878968000000, 2000000, 78, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 94 499) (.both (Sets.deviceExamined 3 499) (.both (Sets.tagged 3 .obj 389 228) (Sets.copiedHere 94 185)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M108

#print axioms Cert.M108.verified
