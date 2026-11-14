import ChainOfProof
open ChainOfProof

namespace Cert.M173

def cited : List Fact := [
  ⟨159, .fileCreated, 1427230546948265, 1, 142, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨242, .fileModified, 1421777886000000, 1, 142, 111⟩,
  ⟨457, .tag, 1794614400000000, 1, 142, 248⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 159 500) (.both (Sets.copiedHere 159 242) (Sets.tagged 159 .obj 457 248))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M173

#print axioms Cert.M173.verified
