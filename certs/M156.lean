import ChainOfProof
open ChainOfProof

namespace Cert.M156

def cited : List Fact := [
  ⟨142, .fileCreated, 1427230519305016, 1, 125, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨216, .fileModified, 1420473442000000, 1, 125, 111⟩,
  ⟨446, .tag, 1794614400000000, 1, 125, 241⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 142 500) (.both (Sets.copiedHere 142 216) (Sets.tagged 142 .obj 446 241))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M156

#print axioms Cert.M156.verified
