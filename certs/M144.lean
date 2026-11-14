import ChainOfProof
open ChainOfProof

namespace Cert.M144

def cited : List Fact := [
  ⟨130, .fileCreated, 1427230482676152, 1, 113, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨204, .fileModified, 1418746226000000, 1, 113, 111⟩,
  ⟨433, .tag, 1794614400000000, 1, 113, 232⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 130 500) (.both (Sets.copiedHere 130 204) (Sets.tagged 130 .obj 433 232))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M144

#print axioms Cert.M144.verified
