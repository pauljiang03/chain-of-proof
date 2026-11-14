import ChainOfProof
open ChainOfProof

namespace Cert.M157

def cited : List Fact := [
  ⟨143, .fileCreated, 1427230522487422, 1, 126, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨227, .fileModified, 1421087022000000, 1, 126, 111⟩,
  ⟨444, .tag, 1794614400000000, 1, 126, 242⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 143 500) (.both (Sets.copiedHere 143 227) (Sets.tagged 143 .obj 444 242))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M157

#print axioms Cert.M157.verified
