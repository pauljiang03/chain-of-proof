import ChainOfProof
open ChainOfProof

namespace Cert.M110

def cited : List Fact := [
  ⟨96, .fileCreated, 1427144130130000, 10000, 80, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨389, .tag, 1794614400000000, 1, 2, 228⟩,
  ⟨195, .fileModified, 1367955476000000, 2000000, 80, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 96 499) (.both (Sets.deviceExamined 3 499) (.both (Sets.tagged 3 .obj 389 228) (Sets.copiedHere 96 195)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M110

#print axioms Cert.M110.verified
