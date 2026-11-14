import ChainOfProof
open ChainOfProof

namespace Cert.M185

def cited : List Fact := [
  ⟨196, .fileModified, 1417459826000000, 1, 118, 111⟩,
  ⟨436, .tag, 1794614400000000, 1, 118, 238⟩,
  ⟨135, .fileCreated, 1427230501973386, 1, 118, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨197, .fileModified, 1417459826000000, 1, 119, 111⟩,
  ⟨440, .tag, 1794614400000000, 1, 119, 238⟩,
  ⟨136, .fileCreated, 1427230501973386, 1, 119, 111⟩,
  ⟨198, .fileModified, 1417459826000000, 2000000, 96, 69⟩,
  ⟨417, .tag, 1794614400000000, 1, 96, 238⟩,
  ⟨112, .fileCreated, 1427205579710000, 10000, 96, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := .both (Sets.fileModifiedAt 196) (.both (Sets.tagged 196 .obj 436 238) (.both (Sets.recoveredOnDevice 135 500) (.both (Sets.fileModifiedAt 197) (.both (Sets.tagged 197 .obj 440 238) (.both (Sets.recoveredOnDevice 136 500) (.both (Sets.fileModifiedAt 198) (.both (Sets.tagged 198 .obj 417 238) (Sets.recoveredOnDevice 112 499))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M185

#print axioms Cert.M185.verified
