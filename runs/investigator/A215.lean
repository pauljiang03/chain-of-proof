import ChainOfProof
open ChainOfProof

namespace Cert.A215

def cited : List Fact := [
  ⟨117, .fileCreated, 1427205584860000, 10000, 101, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨341, .tag, 1794614400000000, 1, 101, 200⟩,
  ⟨161, .fileModified, 1418939458000000, 10000, 53, 19⟩,
  ⟨330, .tag, 1794614400000000, 1, 53, 200⟩,
  ⟨329, .tag, 1794614400000000, 1, 53, 197⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 117 376) (.both (Sets.tagged 117 .obj 341 200) (.both (Sets.tagged 161 .obj 330 200) (Sets.tagged 161 .obj 329 197)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A215

#print axioms Cert.A215.verified
