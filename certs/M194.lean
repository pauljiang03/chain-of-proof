import ChainOfProof
open ChainOfProof

namespace Cert.M194

def cited : List Fact := [
  ⟨245, .fileModified, 1421784300000000, 1, 140, 111⟩,
  ⟨456, .tag, 1794614400000000, 1, 140, 247⟩,
  ⟨157, .fileCreated, 1427230545934263, 1, 140, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨246, .fileModified, 1421784300000000, 1, 141, 111⟩,
  ⟨462, .tag, 1794614400000000, 1, 141, 247⟩,
  ⟨158, .fileCreated, 1427230545934263, 1, 141, 111⟩,
  ⟨247, .fileModified, 1421784300000000, 2000000, 107, 69⟩,
  ⟨428, .tag, 1794614400000000, 1, 107, 247⟩,
  ⟨123, .fileCreated, 1427205615650000, 10000, 107, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := .both (Sets.fileModifiedAt 245) (.both (Sets.tagged 245 .obj 456 247) (.both (Sets.recoveredOnDevice 157 500) (.both (Sets.fileModifiedAt 246) (.both (Sets.tagged 246 .obj 462 247) (.both (Sets.recoveredOnDevice 158 500) (.both (Sets.fileModifiedAt 247) (.both (Sets.tagged 247 .obj 428 247) (Sets.recoveredOnDevice 123 499))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M194

#print axioms Cert.M194.verified
