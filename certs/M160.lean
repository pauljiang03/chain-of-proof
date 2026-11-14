import ChainOfProof
open ChainOfProof

namespace Cert.M160

def cited : List Fact := [
  ⟨146, .fileCreated, 1427230522908622, 1, 129, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨208, .fileModified, 1418939458000000, 1, 129, 111⟩,
  ⟨450, .tag, 1794614400000000, 1, 129, 234⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 146 500) (.both (Sets.copiedHere 146 208) (Sets.tagged 146 .obj 450 234))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M160

#print axioms Cert.M160.verified
