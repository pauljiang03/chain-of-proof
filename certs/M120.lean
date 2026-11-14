import ChainOfProof
open ChainOfProof

namespace Cert.M120

def cited : List Fact := [
  ⟨106, .fileCreated, 1427144137180000, 10000, 90, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨315, .tag, 1794614400000000, 1, 2, 194⟩,
  ⟨151, .fileModified, 1367953850000000, 2000000, 90, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 106 376) (.both (Sets.deviceExamined 3 376) (.both (Sets.tagged 3 .obj 315 194) (Sets.copiedHere 106 151)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M120

#print axioms Cert.M120.verified
