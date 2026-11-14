import ChainOfProof
open ChainOfProof

namespace Cert.M138

def cited : List Fact := [
  ⟨124, .fileCreated, 1427205618410000, 10000, 108, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨389, .tag, 1794614400000000, 1, 2, 228⟩,
  ⟨244, .fileModified, 1421777886000000, 2000000, 108, 69⟩,
  ⟨429, .tag, 1794614400000000, 1, 108, 248⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 124 499) (.both (Sets.deviceExamined 3 499) (.both (Sets.tagged 3 .obj 389 228) (.both (.before 3 124) (.both (Sets.copiedHere 124 244) (Sets.tagged 124 .obj 429 248)))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M138

#print axioms Cert.M138.verified
