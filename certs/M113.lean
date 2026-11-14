import ChainOfProof
open ChainOfProof

namespace Cert.M113

def cited : List Fact := [
  ⟨99, .fileCreated, 1427144132760000, 10000, 83, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨315, .tag, 1794614400000000, 1, 2, 194⟩,
  ⟨139, .fileModified, 1264362300000000, 2000000, 83, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 99 376) (.both (Sets.deviceExamined 3 376) (.both (Sets.tagged 3 .obj 315 194) (Sets.copiedHere 99 139)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M113

#print axioms Cert.M113.verified
