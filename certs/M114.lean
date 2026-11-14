import ChainOfProof
open ChainOfProof

namespace Cert.M114

def cited : List Fact := [
  ⟨100, .fileCreated, 1427144133200000, 10000, 84, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨389, .tag, 1794614400000000, 1, 2, 228⟩,
  ⟨186, .fileModified, 1358879424000000, 2000000, 84, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 100 499) (.both (Sets.deviceExamined 3 499) (.both (Sets.tagged 3 .obj 389 228) (Sets.copiedHere 100 186)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M114

#print axioms Cert.M114.verified
