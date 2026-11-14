import ChainOfProof
open ChainOfProof

namespace Cert.M170

def cited : List Fact := [
  ⟨156, .fileCreated, 1427230545325862, 1, 139, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨231, .fileModified, 1421090426000000, 1, 139, 111⟩,
  ⟨461, .tag, 1794614400000000, 1, 139, 246⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 156 500) (.both (Sets.copiedHere 156 231) (Sets.tagged 156 .obj 461 246))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M170

#print axioms Cert.M170.verified
