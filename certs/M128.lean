import ChainOfProof
open ChainOfProof

namespace Cert.M128

def cited : List Fact := [
  ⟨114, .fileCreated, 1427205583520000, 10000, 98, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨315, .tag, 1794614400000000, 1, 2, 194⟩,
  ⟨173, .fileModified, 1421766824000000, 2000000, 98, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 114 376) (.both (Sets.deviceExamined 3 376) (.both (Sets.tagged 3 .obj 315 194) (.both (.before 3 114) (Sets.copiedHere 114 173))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M128

#print axioms Cert.M128.verified
