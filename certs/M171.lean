import ChainOfProof
open ChainOfProof

namespace Cert.M171

def cited : List Fact := [
  ⟨157, .fileCreated, 1427230545934263, 1, 140, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨245, .fileModified, 1421784300000000, 1, 140, 111⟩,
  ⟨456, .tag, 1794614400000000, 1, 140, 247⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 157 500) (.both (Sets.copiedHere 157 245) (Sets.tagged 157 .obj 456 247))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M171

#print axioms Cert.M171.verified
