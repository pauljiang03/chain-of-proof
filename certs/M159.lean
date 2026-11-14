import ChainOfProof
open ChainOfProof

namespace Cert.M159

def cited : List Fact := [
  ⟨145, .fileCreated, 1427230522908622, 1, 128, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨207, .fileModified, 1418939458000000, 1, 128, 111⟩,
  ⟨448, .tag, 1794614400000000, 1, 128, 234⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 145 500) (.both (Sets.copiedHere 145 207) (Sets.tagged 145 .obj 448 234))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M159

#print axioms Cert.M159.verified
