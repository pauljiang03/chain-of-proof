import ChainOfProof
open ChainOfProof

namespace Cert.M153

def cited : List Fact := [
  ⟨139, .fileCreated, 1427230519071016, 1, 122, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨239, .fileModified, 1421766824000000, 1, 122, 111⟩,
  ⟨442, .tag, 1794614400000000, 1, 122, 240⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 139 500) (.both (Sets.copiedHere 139 239) (Sets.tagged 139 .obj 442 240))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M153

#print axioms Cert.M153.verified
