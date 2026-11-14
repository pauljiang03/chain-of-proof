import ChainOfProof
open ChainOfProof

namespace Cert.M168

def cited : List Fact := [
  ⟨154, .fileCreated, 1427230543968659, 1, 137, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨234, .fileModified, 1421097940000000, 1, 137, 111⟩,
  ⟨460, .tag, 1794614400000000, 1, 137, 245⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 154 500) (.both (Sets.copiedHere 154 234) (Sets.tagged 154 .obj 460 245))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M168

#print axioms Cert.M168.verified
