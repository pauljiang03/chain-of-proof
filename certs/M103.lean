import ChainOfProof
open ChainOfProof

namespace Cert.M103

def cited : List Fact := [
  ⟨89, .fileCreated, 1427144120630000, 10000, 73, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨315, .tag, 1794614400000000, 1, 2, 194⟩,
  ⟨148, .fileModified, 1367952524000000, 2000000, 73, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 89 376) (.both (Sets.deviceExamined 3 376) (.both (Sets.tagged 3 .obj 315 194) (Sets.copiedHere 89 148)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M103

#print axioms Cert.M103.verified
