import ChainOfProof
open ChainOfProof

namespace Cert.M192

def cited : List Fact := [
  ⟨233, .fileModified, 1421097940000000, 1, 136, 111⟩,
  ⟨454, .tag, 1794614400000000, 1, 136, 245⟩,
  ⟨153, .fileCreated, 1427230543968659, 1, 136, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨234, .fileModified, 1421097940000000, 1, 137, 111⟩,
  ⟨460, .tag, 1794614400000000, 1, 137, 245⟩,
  ⟨154, .fileCreated, 1427230543968659, 1, 137, 111⟩,
  ⟨235, .fileModified, 1421097940000000, 2000000, 105, 69⟩,
  ⟨426, .tag, 1794614400000000, 1, 105, 245⟩,
  ⟨121, .fileCreated, 1427205613550000, 10000, 105, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := .both (Sets.fileModifiedAt 233) (.both (Sets.tagged 233 .obj 454 245) (.both (Sets.recoveredOnDevice 153 500) (.both (Sets.fileModifiedAt 234) (.both (Sets.tagged 234 .obj 460 245) (.both (Sets.recoveredOnDevice 154 500) (.both (Sets.fileModifiedAt 235) (.both (Sets.tagged 235 .obj 426 245) (Sets.recoveredOnDevice 121 499))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M192

#print axioms Cert.M192.verified
