import ChainOfProof
open ChainOfProof

namespace Cert.M099

def cited : List Fact := [
  ⟨85, .fileCreated, 1427144117150000, 10000, 68, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨389, .tag, 1794614400000000, 1, 2, 228⟩,
  ⟨194, .fileModified, 1367954382000000, 2000000, 68, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 85 499) (.both (Sets.deviceExamined 3 499) (.both (Sets.tagged 3 .obj 389 228) (Sets.copiedHere 85 194)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M099

#print axioms Cert.M099.verified
