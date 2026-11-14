import ChainOfProof
open ChainOfProof

namespace Cert.M184

def cited : List Fact := [
  ⟨224, .fileModified, 1420751304000000, 1, 116, 111⟩,
  ⟨435, .tag, 1794614400000000, 1, 116, 237⟩,
  ⟨133, .fileCreated, 1427230501427385, 1, 116, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨225, .fileModified, 1420751304000000, 1, 117, 111⟩,
  ⟨439, .tag, 1794614400000000, 1, 117, 237⟩,
  ⟨134, .fileCreated, 1427230501427385, 1, 117, 111⟩,
  ⟨226, .fileModified, 1420751304000000, 2000000, 95, 69⟩,
  ⟨416, .tag, 1794614400000000, 1, 95, 237⟩,
  ⟨111, .fileCreated, 1427205579680000, 10000, 95, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := .both (Sets.fileModifiedAt 224) (.both (Sets.tagged 224 .obj 435 237) (.both (Sets.recoveredOnDevice 133 500) (.both (Sets.fileModifiedAt 225) (.both (Sets.tagged 225 .obj 439 237) (.both (Sets.recoveredOnDevice 134 500) (.both (Sets.fileModifiedAt 226) (.both (Sets.tagged 226 .obj 416 237) (Sets.recoveredOnDevice 111 499))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M184

#print axioms Cert.M184.verified
