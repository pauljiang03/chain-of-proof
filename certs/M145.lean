import ChainOfProof
open ChainOfProof

namespace Cert.M145

def cited : List Fact := [
  ⟨131, .fileCreated, 1427230501021784, 1, 114, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨236, .fileModified, 1421435424000000, 1, 114, 111⟩,
  ⟨434, .tag, 1794614400000000, 1, 114, 236⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 131 500) (.both (Sets.copiedHere 131 236) (Sets.tagged 131 .obj 434 236))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M145

#print axioms Cert.M145.verified
