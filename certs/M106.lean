import ChainOfProof
open ChainOfProof

namespace Cert.M106

def cited : List Fact := [
  ⟨92, .fileCreated, 1427144126870000, 10000, 76, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨315, .tag, 1794614400000000, 1, 2, 194⟩,
  ⟨128, .fileModified, 1097745676000000, 2000000, 76, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 92 376) (.both (Sets.deviceExamined 3 376) (.both (Sets.tagged 3 .obj 315 194) (Sets.copiedHere 92 128)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M106

#print axioms Cert.M106.verified
