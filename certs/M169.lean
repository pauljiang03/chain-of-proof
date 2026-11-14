import ChainOfProof
open ChainOfProof

namespace Cert.M169

def cited : List Fact := [
  ⟨155, .fileCreated, 1427230545325862, 1, 138, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨230, .fileModified, 1421090426000000, 1, 138, 111⟩,
  ⟨455, .tag, 1794614400000000, 1, 138, 246⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 155 500) (.both (Sets.copiedHere 155 230) (Sets.tagged 155 .obj 455 246))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M169

#print axioms Cert.M169.verified
