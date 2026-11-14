import ChainOfProof
open ChainOfProof

namespace Cert.M101

def cited : List Fact := [
  ⟨87, .fileCreated, 1427144119270000, 10000, 71, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨389, .tag, 1794614400000000, 1, 2, 228⟩,
  ⟨181, .fileModified, 1358878658000000, 2000000, 71, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 87 499) (.both (Sets.deviceExamined 3 499) (.both (Sets.tagged 3 .obj 389 228) (Sets.copiedHere 87 181)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M101

#print axioms Cert.M101.verified
