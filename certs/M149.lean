import ChainOfProof
open ChainOfProof

namespace Cert.M149

def cited : List Fact := [
  ⟨135, .fileCreated, 1427230501973386, 1, 118, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨196, .fileModified, 1417459826000000, 1, 118, 111⟩,
  ⟨436, .tag, 1794614400000000, 1, 118, 238⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 135 500) (.both (Sets.copiedHere 135 196) (Sets.tagged 135 .obj 436 238))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M149

#print axioms Cert.M149.verified
