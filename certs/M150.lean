import ChainOfProof
open ChainOfProof

namespace Cert.M150

def cited : List Fact := [
  ⟨136, .fileCreated, 1427230501973386, 1, 119, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨197, .fileModified, 1417459826000000, 1, 119, 111⟩,
  ⟨440, .tag, 1794614400000000, 1, 119, 238⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 136 500) (.both (Sets.copiedHere 136 197) (Sets.tagged 136 .obj 440 238))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M150

#print axioms Cert.M150.verified
