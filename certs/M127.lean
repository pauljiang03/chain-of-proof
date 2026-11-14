import ChainOfProof
open ChainOfProof

namespace Cert.M127

def cited : List Fact := [
  ⟨113, .fileCreated, 1427205580710000, 10000, 97, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨389, .tag, 1794614400000000, 1, 2, 228⟩,
  ⟨201, .fileModified, 1417541338000000, 2000000, 97, 69⟩,
  ⟨418, .tag, 1794614400000000, 1, 97, 239⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 113 499) (.both (Sets.deviceExamined 3 499) (.both (Sets.tagged 3 .obj 389 228) (.both (.before 3 113) (.both (Sets.copiedHere 113 201) (Sets.tagged 113 .obj 418 239)))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M127

#print axioms Cert.M127.verified
