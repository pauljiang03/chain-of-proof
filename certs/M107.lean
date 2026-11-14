import ChainOfProof
open ChainOfProof

namespace Cert.M107

def cited : List Fact := [
  ⟨93, .fileCreated, 1427144127180000, 10000, 77, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨389, .tag, 1794614400000000, 1, 2, 228⟩,
  ⟨184, .fileModified, 1358878896000000, 2000000, 77, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 93 499) (.both (Sets.deviceExamined 3 499) (.both (Sets.tagged 3 .obj 389 228) (Sets.copiedHere 93 184)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M107

#print axioms Cert.M107.verified
