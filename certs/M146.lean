import ChainOfProof
open ChainOfProof

namespace Cert.M146

def cited : List Fact := [
  ⟨132, .fileCreated, 1427230501021784, 1, 115, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨237, .fileModified, 1421435424000000, 1, 115, 111⟩,
  ⟨438, .tag, 1794614400000000, 1, 115, 236⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 132 500) (.both (Sets.copiedHere 132 237) (Sets.tagged 132 .obj 438 236))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M146

#print axioms Cert.M146.verified
