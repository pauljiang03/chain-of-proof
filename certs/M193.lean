import ChainOfProof
open ChainOfProof

namespace Cert.M193

def cited : List Fact := [
  ⟨230, .fileModified, 1421090426000000, 1, 138, 111⟩,
  ⟨455, .tag, 1794614400000000, 1, 138, 246⟩,
  ⟨155, .fileCreated, 1427230545325862, 1, 138, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨231, .fileModified, 1421090426000000, 1, 139, 111⟩,
  ⟨461, .tag, 1794614400000000, 1, 139, 246⟩,
  ⟨156, .fileCreated, 1427230545325862, 1, 139, 111⟩,
  ⟨232, .fileModified, 1421090426000000, 2000000, 106, 69⟩,
  ⟨427, .tag, 1794614400000000, 1, 106, 246⟩,
  ⟨122, .fileCreated, 1427205614340000, 10000, 106, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := .both (Sets.fileModifiedAt 230) (.both (Sets.tagged 230 .obj 455 246) (.both (Sets.recoveredOnDevice 155 500) (.both (Sets.fileModifiedAt 231) (.both (Sets.tagged 231 .obj 461 246) (.both (Sets.recoveredOnDevice 156 500) (.both (Sets.fileModifiedAt 232) (.both (Sets.tagged 232 .obj 427 246) (Sets.recoveredOnDevice 122 499))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M193

#print axioms Cert.M193.verified
