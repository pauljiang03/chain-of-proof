import ChainOfProof
open ChainOfProof

namespace Cert.A065

def cited : List Fact := [
  ⟨162, .fileModified, 1418939458000000, 2000000, 101, 69⟩,
  ⟨341, .tag, 1794614400000000, 1, 101, 200⟩,
  ⟨161, .fileModified, 1418939458000000, 10000, 53, 19⟩,
  ⟨330, .tag, 1794614400000000, 1, 53, 200⟩,
  ⟨117, .fileCreated, 1427205584860000, 10000, 101, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := .both (Sets.tagged 162 .obj 341 200) (.both (Sets.tagged 161 .obj 330 200) (Sets.recoveredOnDevice 117 376))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A065

#print axioms Cert.A065.verified
