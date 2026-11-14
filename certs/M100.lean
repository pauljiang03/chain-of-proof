import ChainOfProof
open ChainOfProof

namespace Cert.M100

def cited : List Fact := [
  ⟨86, .fileCreated, 1427144117410000, 10000, 70, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨315, .tag, 1794614400000000, 1, 2, 194⟩,
  ⟨140, .fileModified, 1358878452000000, 2000000, 70, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 86 376) (.both (Sets.deviceExamined 3 376) (.both (Sets.tagged 3 .obj 315 194) (Sets.copiedHere 86 140)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M100

#print axioms Cert.M100.verified
