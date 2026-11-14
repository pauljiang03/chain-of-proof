import ChainOfProof
open ChainOfProof

namespace Cert.M117

def cited : List Fact := [
  ⟨103, .fileCreated, 1427144136010000, 10000, 87, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨389, .tag, 1794614400000000, 1, 2, 228⟩,
  ⟨167, .fileModified, 1097745684000000, 2000000, 87, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 103 499) (.both (Sets.deviceExamined 3 499) (.both (Sets.tagged 3 .obj 389 228) (Sets.copiedHere 103 167)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M117

#print axioms Cert.M117.verified
