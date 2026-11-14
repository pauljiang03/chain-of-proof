import ChainOfProof
open ChainOfProof

namespace Cert.M105

def cited : List Fact := [
  ⟨91, .fileCreated, 1427144124710000, 10000, 75, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨315, .tag, 1794614400000000, 1, 2, 194⟩,
  ⟨143, .fileModified, 1358878838000000, 2000000, 75, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 91 376) (.both (Sets.deviceExamined 3 376) (.both (Sets.tagged 3 .obj 315 194) (Sets.copiedHere 91 143)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M105

#print axioms Cert.M105.verified
