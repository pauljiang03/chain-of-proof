import ChainOfProof
open ChainOfProof

namespace Cert.M181

def cited : List Fact := [
  ⟨207, .fileModified, 1418939458000000, 1, 128, 111⟩,
  ⟨448, .tag, 1794614400000000, 1, 128, 234⟩,
  ⟨145, .fileCreated, 1427230522908622, 1, 128, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨208, .fileModified, 1418939458000000, 1, 129, 111⟩,
  ⟨450, .tag, 1794614400000000, 1, 129, 234⟩,
  ⟨146, .fileCreated, 1427230522908622, 1, 129, 111⟩,
  ⟨209, .fileModified, 1418939458000000, 10000, 53, 19⟩,
  ⟨404, .tag, 1794614400000000, 1, 53, 234⟩,
  ⟨403, .tag, 1794614400000000, 1, 53, 231⟩,
  ⟨210, .fileModified, 1418939458000000, 2000000, 101, 69⟩,
  ⟨422, .tag, 1794614400000000, 1, 101, 234⟩,
  ⟨117, .fileCreated, 1427205584860000, 10000, 101, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := .both (Sets.fileModifiedAt 207) (.both (Sets.tagged 207 .obj 448 234) (.both (Sets.recoveredOnDevice 145 500) (.both (Sets.fileModifiedAt 208) (.both (Sets.tagged 208 .obj 450 234) (.both (Sets.recoveredOnDevice 146 500) (.both (Sets.fileModifiedAt 209) (.both (Sets.tagged 209 .obj 404 234) (.both (Sets.tagged 209 .obj 403 231) (.both (Sets.fileModifiedAt 210) (.both (Sets.tagged 210 .obj 422 234) (Sets.recoveredOnDevice 117 499)))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M181

#print axioms Cert.M181.verified
