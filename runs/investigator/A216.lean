import ChainOfProof
open ChainOfProof

namespace Cert.A216

def cited : List Fact := [
  ⟨118, .fileCreated, 1427205606780000, 10000, 102, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨342, .tag, 1794614400000000, 1, 102, 201⟩,
  ⟨163, .fileModified, 1419018826000000, 10000, 18, 19⟩,
  ⟨332, .tag, 1794614400000000, 1, 18, 201⟩,
  ⟨331, .tag, 1794614400000000, 1, 18, 197⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 118 376) (.both (Sets.tagged 118 .obj 342 201) (.both (Sets.tagged 163 .obj 332 201) (Sets.tagged 163 .obj 331 197)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A216

#print axioms Cert.A216.verified
