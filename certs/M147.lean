import ChainOfProof
open ChainOfProof

namespace Cert.M147

def cited : List Fact := [
  ⟨133, .fileCreated, 1427230501427385, 1, 116, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨224, .fileModified, 1420751304000000, 1, 116, 111⟩,
  ⟨435, .tag, 1794614400000000, 1, 116, 237⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 133 500) (.both (Sets.copiedHere 133 224) (Sets.tagged 133 .obj 435 237))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M147

#print axioms Cert.M147.verified
