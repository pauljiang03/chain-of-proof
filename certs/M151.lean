import ChainOfProof
open ChainOfProof

namespace Cert.M151

def cited : List Fact := [
  ⟨137, .fileCreated, 1427230507090195, 1, 120, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨199, .fileModified, 1417541338000000, 1, 120, 111⟩,
  ⟨437, .tag, 1794614400000000, 1, 120, 239⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 137 500) (.both (Sets.copiedHere 137 199) (Sets.tagged 137 .obj 437 239))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M151

#print axioms Cert.M151.verified
