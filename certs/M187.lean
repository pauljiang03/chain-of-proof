import ChainOfProof
open ChainOfProof

namespace Cert.M187

def cited : List Fact := [
  ⟨239, .fileModified, 1421766824000000, 1, 122, 111⟩,
  ⟨442, .tag, 1794614400000000, 1, 122, 240⟩,
  ⟨139, .fileCreated, 1427230519071016, 1, 122, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨240, .fileModified, 1421766824000000, 1, 123, 111⟩,
  ⟨445, .tag, 1794614400000000, 1, 123, 240⟩,
  ⟨140, .fileCreated, 1427230519071016, 1, 123, 111⟩,
  ⟨241, .fileModified, 1421766824000000, 2000000, 98, 69⟩,
  ⟨419, .tag, 1794614400000000, 1, 98, 240⟩,
  ⟨114, .fileCreated, 1427205583520000, 10000, 98, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := .both (Sets.fileModifiedAt 239) (.both (Sets.tagged 239 .obj 442 240) (.both (Sets.recoveredOnDevice 139 500) (.both (Sets.fileModifiedAt 240) (.both (Sets.tagged 240 .obj 445 240) (.both (Sets.recoveredOnDevice 140 500) (.both (Sets.fileModifiedAt 241) (.both (Sets.tagged 241 .obj 419 240) (Sets.recoveredOnDevice 114 499))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M187

#print axioms Cert.M187.verified
