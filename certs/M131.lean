import ChainOfProof
open ChainOfProof

namespace Cert.M131

def cited : List Fact := [
  ⟨117, .fileCreated, 1427205584860000, 10000, 101, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨389, .tag, 1794614400000000, 1, 2, 228⟩,
  ⟨210, .fileModified, 1418939458000000, 2000000, 101, 69⟩,
  ⟨422, .tag, 1794614400000000, 1, 101, 234⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 117 499) (.both (Sets.deviceExamined 3 499) (.both (Sets.tagged 3 .obj 389 228) (.both (.before 3 117) (.both (Sets.copiedHere 117 210) (Sets.tagged 117 .obj 422 234)))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M131

#print axioms Cert.M131.verified
