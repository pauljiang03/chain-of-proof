import ChainOfProof
open ChainOfProof

namespace Cert.M161

def cited : List Fact := [
  ⟨147, .fileCreated, 1427230540318253, 1, 130, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨211, .fileModified, 1419018826000000, 1, 130, 111⟩,
  ⟨449, .tag, 1794614400000000, 1, 130, 235⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 147 500) (.both (Sets.copiedHere 147 211) (Sets.tagged 147 .obj 449 235))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M161

#print axioms Cert.M161.verified
