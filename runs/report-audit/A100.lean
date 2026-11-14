import ChainOfProof
open ChainOfProof

namespace Cert.A100

def cited : List Fact := [
  ⟨126, .fileCreated, 1427226707220000, 10000, 109, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 126 376) (.before 3 126)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A100

#print axioms Cert.A100.verified
