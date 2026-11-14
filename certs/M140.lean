import ChainOfProof
open ChainOfProof

namespace Cert.M140

def cited : List Fact := [
  ⟨126, .fileCreated, 1427226707220000, 10000, 109, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨389, .tag, 1794614400000000, 1, 2, 228⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 126 499) (.both (Sets.deviceExamined 3 499) (.both (Sets.tagged 3 .obj 389 228) (.before 3 126)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M140

#print axioms Cert.M140.verified
