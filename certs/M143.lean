import ChainOfProof
open ChainOfProof

namespace Cert.M143

def cited : List Fact := [
  ⟨129, .fileCreated, 1427230482676152, 1, 34, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨203, .fileModified, 1418746226000000, 1, 34, 111⟩,
  ⟨431, .tag, 1794614400000000, 1, 34, 232⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 129 500) (.both (Sets.copiedHere 129 203) (Sets.tagged 129 .obj 431 232))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M143

#print axioms Cert.M143.verified
