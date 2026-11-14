import ChainOfProof
open ChainOfProof

namespace Cert.M148

def cited : List Fact := [
  ⟨134, .fileCreated, 1427230501427385, 1, 117, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨225, .fileModified, 1420751304000000, 1, 117, 111⟩,
  ⟨439, .tag, 1794614400000000, 1, 117, 237⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 134 500) (.both (Sets.copiedHere 134 225) (Sets.tagged 134 .obj 439 237))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M148

#print axioms Cert.M148.verified
