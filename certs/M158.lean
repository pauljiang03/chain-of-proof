import ChainOfProof
open ChainOfProof

namespace Cert.M158

def cited : List Fact := [
  ⟨144, .fileCreated, 1427230522487422, 1, 127, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨228, .fileModified, 1421087022000000, 1, 127, 111⟩,
  ⟨447, .tag, 1794614400000000, 1, 127, 242⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 144 500) (.both (Sets.copiedHere 144 228) (Sets.tagged 144 .obj 447 242))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M158

#print axioms Cert.M158.verified
