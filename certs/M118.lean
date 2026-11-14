import ChainOfProof
open ChainOfProof

namespace Cert.M118

def cited : List Fact := [
  ⟨104, .fileCreated, 1427144136210000, 10000, 88, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨389, .tag, 1794614400000000, 1, 2, 228⟩,
  ⟨166, .fileModified, 1097745680000000, 2000000, 88, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 104 499) (.both (Sets.deviceExamined 3 499) (.both (Sets.tagged 3 .obj 389 228) (Sets.copiedHere 104 166)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M118

#print axioms Cert.M118.verified
