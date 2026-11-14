import ChainOfProof
open ChainOfProof

namespace Cert.M189

def cited : List Fact := [
  ⟨227, .fileModified, 1421087022000000, 1, 126, 111⟩,
  ⟨444, .tag, 1794614400000000, 1, 126, 242⟩,
  ⟨143, .fileCreated, 1427230522487422, 1, 126, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨228, .fileModified, 1421087022000000, 1, 127, 111⟩,
  ⟨447, .tag, 1794614400000000, 1, 127, 242⟩,
  ⟨144, .fileCreated, 1427230522487422, 1, 127, 111⟩,
  ⟨229, .fileModified, 1421087022000000, 2000000, 100, 69⟩,
  ⟨421, .tag, 1794614400000000, 1, 100, 242⟩,
  ⟨116, .fileCreated, 1427205584810000, 10000, 100, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := .both (Sets.fileModifiedAt 227) (.both (Sets.tagged 227 .obj 444 242) (.both (Sets.recoveredOnDevice 143 500) (.both (Sets.fileModifiedAt 228) (.both (Sets.tagged 228 .obj 447 242) (.both (Sets.recoveredOnDevice 144 500) (.both (Sets.fileModifiedAt 229) (.both (Sets.tagged 229 .obj 421 242) (Sets.recoveredOnDevice 116 499))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M189

#print axioms Cert.M189.verified
