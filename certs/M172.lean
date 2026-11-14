import ChainOfProof
open ChainOfProof

namespace Cert.M172

def cited : List Fact := [
  ⟨158, .fileCreated, 1427230545934263, 1, 141, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨246, .fileModified, 1421784300000000, 1, 141, 111⟩,
  ⟨462, .tag, 1794614400000000, 1, 141, 247⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 158 500) (.both (Sets.copiedHere 158 246) (Sets.tagged 158 .obj 462 247))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M172

#print axioms Cert.M172.verified
