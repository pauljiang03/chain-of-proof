import ChainOfProof
open ChainOfProof

namespace Cert.M174

def cited : List Fact := [
  ⟨160, .fileCreated, 1427230546948265, 1, 143, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨243, .fileModified, 1421777886000000, 1, 143, 111⟩,
  ⟨463, .tag, 1794614400000000, 1, 143, 248⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 160 500) (.both (Sets.copiedHere 160 243) (Sets.tagged 160 .obj 463 248))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M174

#print axioms Cert.M174.verified
