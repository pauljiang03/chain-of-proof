import ChainOfProof
open ChainOfProof

namespace Cert.M135

def cited : List Fact := [
  ⟨121, .fileCreated, 1427205613550000, 10000, 105, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨315, .tag, 1794614400000000, 1, 2, 194⟩,
  ⟨171, .fileModified, 1421097940000000, 2000000, 105, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 121 376) (.both (Sets.deviceExamined 3 376) (.both (Sets.tagged 3 .obj 315 194) (.both (.before 3 121) (Sets.copiedHere 121 171))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M135

#print axioms Cert.M135.verified
