import ChainOfProof
open ChainOfProof

namespace Cert.M183

def cited : List Fact := [
  ⟨236, .fileModified, 1421435424000000, 1, 114, 111⟩,
  ⟨434, .tag, 1794614400000000, 1, 114, 236⟩,
  ⟨131, .fileCreated, 1427230501021784, 1, 114, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨237, .fileModified, 1421435424000000, 1, 115, 111⟩,
  ⟨438, .tag, 1794614400000000, 1, 115, 236⟩,
  ⟨132, .fileCreated, 1427230501021784, 1, 115, 111⟩,
  ⟨238, .fileModified, 1421435424000000, 2000000, 94, 69⟩,
  ⟨415, .tag, 1794614400000000, 1, 94, 236⟩,
  ⟨110, .fileCreated, 1427205579580000, 10000, 94, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := .both (Sets.fileModifiedAt 236) (.both (Sets.tagged 236 .obj 434 236) (.both (Sets.recoveredOnDevice 131 500) (.both (Sets.fileModifiedAt 237) (.both (Sets.tagged 237 .obj 438 236) (.both (Sets.recoveredOnDevice 132 500) (.both (Sets.fileModifiedAt 238) (.both (Sets.tagged 238 .obj 415 236) (Sets.recoveredOnDevice 110 499))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M183

#print axioms Cert.M183.verified
