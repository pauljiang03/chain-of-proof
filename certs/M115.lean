import ChainOfProof
open ChainOfProof

namespace Cert.M115

def cited : List Fact := [
  ⟨101, .fileCreated, 1427144135420000, 10000, 85, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨389, .tag, 1794614400000000, 1, 2, 228⟩,
  ⟨169, .fileModified, 1113140946000000, 2000000, 85, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 101 499) (.both (Sets.deviceExamined 3 499) (.both (Sets.tagged 3 .obj 389 228) (Sets.copiedHere 101 169)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M115

#print axioms Cert.M115.verified
