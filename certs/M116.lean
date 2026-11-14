import ChainOfProof
open ChainOfProof

namespace Cert.M116

def cited : List Fact := [
  ⟨102, .fileCreated, 1427144135830000, 10000, 86, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨389, .tag, 1794614400000000, 1, 2, 228⟩,
  ⟨168, .fileModified, 1113140944000000, 2000000, 86, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 102 499) (.both (Sets.deviceExamined 3 499) (.both (Sets.tagged 3 .obj 389 228) (Sets.copiedHere 102 168)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M116

#print axioms Cert.M116.verified
