import ChainOfProof
open ChainOfProof

namespace Cert.M136

def cited : List Fact := [
  ⟨122, .fileCreated, 1427205614340000, 10000, 106, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨315, .tag, 1794614400000000, 1, 2, 194⟩,
  ⟨170, .fileModified, 1421090426000000, 2000000, 106, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 122 376) (.both (Sets.deviceExamined 3 376) (.both (Sets.tagged 3 .obj 315 194) (.both (.before 3 122) (Sets.copiedHere 122 170))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M136

#print axioms Cert.M136.verified
