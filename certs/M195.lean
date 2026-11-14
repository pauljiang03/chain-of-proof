import ChainOfProof
open ChainOfProof

namespace Cert.M195

def cited : List Fact := [
  ⟨242, .fileModified, 1421777886000000, 1, 142, 111⟩,
  ⟨457, .tag, 1794614400000000, 1, 142, 248⟩,
  ⟨159, .fileCreated, 1427230546948265, 1, 142, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨243, .fileModified, 1421777886000000, 1, 143, 111⟩,
  ⟨463, .tag, 1794614400000000, 1, 143, 248⟩,
  ⟨160, .fileCreated, 1427230546948265, 1, 143, 111⟩,
  ⟨244, .fileModified, 1421777886000000, 2000000, 108, 69⟩,
  ⟨429, .tag, 1794614400000000, 1, 108, 248⟩,
  ⟨124, .fileCreated, 1427205618410000, 10000, 108, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := .both (Sets.fileModifiedAt 242) (.both (Sets.tagged 242 .obj 457 248) (.both (Sets.recoveredOnDevice 159 500) (.both (Sets.fileModifiedAt 243) (.both (Sets.tagged 243 .obj 463 248) (.both (Sets.recoveredOnDevice 160 500) (.both (Sets.fileModifiedAt 244) (.both (Sets.tagged 244 .obj 429 248) (Sets.recoveredOnDevice 124 499))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M195

#print axioms Cert.M195.verified
