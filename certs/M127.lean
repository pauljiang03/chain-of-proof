import ChainOfProof
open ChainOfProof

namespace Cert.M127

def cited : List Fact := [
  ⟨113, .fileCreated, 1427205580710000, 10000, 97, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨315, .tag, 1794614400000000, 1, 2, 194⟩,
  ⟨157, .fileModified, 1417541338000000, 2000000, 97, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 113 376) (.both (Sets.deviceExamined 3 376) (.both (Sets.tagged 3 .obj 315 194) (.both (.before 3 113) (Sets.copiedHere 113 157))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M127

#print axioms Cert.M127.verified
