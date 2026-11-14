import ChainOfProof
open ChainOfProof

namespace Cert.M152

def cited : List Fact := [
  ⟨138, .fileCreated, 1427230507090195, 1, 121, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨200, .fileModified, 1417541338000000, 1, 121, 111⟩,
  ⟨441, .tag, 1794614400000000, 1, 121, 239⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 138 500) (.both (Sets.copiedHere 138 200) (Sets.tagged 138 .obj 441 239))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M152

#print axioms Cert.M152.verified
