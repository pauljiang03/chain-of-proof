import ChainOfProof
open ChainOfProof

namespace Cert.M186

def cited : List Fact := [
  ⟨199, .fileModified, 1417541338000000, 1, 120, 111⟩,
  ⟨437, .tag, 1794614400000000, 1, 120, 239⟩,
  ⟨137, .fileCreated, 1427230507090195, 1, 120, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨200, .fileModified, 1417541338000000, 1, 121, 111⟩,
  ⟨441, .tag, 1794614400000000, 1, 121, 239⟩,
  ⟨138, .fileCreated, 1427230507090195, 1, 121, 111⟩,
  ⟨201, .fileModified, 1417541338000000, 2000000, 97, 69⟩,
  ⟨418, .tag, 1794614400000000, 1, 97, 239⟩,
  ⟨113, .fileCreated, 1427205580710000, 10000, 97, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := .both (Sets.fileModifiedAt 199) (.both (Sets.tagged 199 .obj 437 239) (.both (Sets.recoveredOnDevice 137 500) (.both (Sets.fileModifiedAt 200) (.both (Sets.tagged 200 .obj 441 239) (.both (Sets.recoveredOnDevice 138 500) (.both (Sets.fileModifiedAt 201) (.both (Sets.tagged 201 .obj 418 239) (Sets.recoveredOnDevice 113 499))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M186

#print axioms Cert.M186.verified
