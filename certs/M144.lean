import ChainOfProof
open ChainOfProof

namespace Cert.M144

def cited : List Fact := [
  ⟨161, .fileModified, 1418939458000000, 10000, 53, 19⟩,
  ⟨330, .tag, 1794614400000000, 1, 53, 200⟩,
  ⟨329, .tag, 1794614400000000, 1, 53, 197⟩,
  ⟨162, .fileModified, 1418939458000000, 2000000, 101, 69⟩,
  ⟨341, .tag, 1794614400000000, 1, 101, 200⟩,
  ⟨117, .fileCreated, 1427205584860000, 10000, 101, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := .both (Sets.fileModifiedAt 161) (.both (Sets.tagged 161 .obj 330 200) (.both (Sets.tagged 161 .obj 329 197) (.both (Sets.fileModifiedAt 162) (.both (Sets.tagged 162 .obj 341 200) (Sets.recoveredOnDevice 117 376)))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M144

#print axioms Cert.M144.verified
