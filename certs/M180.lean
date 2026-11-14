import ChainOfProof
open ChainOfProof

namespace Cert.M180

def cited : List Fact := [
  ⟨248, .fileModified, 1422046030000000, 1, 110, 111⟩,
  ⟨430, .tag, 1794614400000000, 1, 110, 233⟩,
  ⟨127, .fileCreated, 1427230456775489, 1, 110, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨249, .fileModified, 1422046030000000, 1, 112, 111⟩,
  ⟨432, .tag, 1794614400000000, 1, 112, 233⟩,
  ⟨128, .fileCreated, 1427230456775489, 1, 112, 111⟩,
  ⟨250, .fileModified, 1422046030000000, 10000, 52, 19⟩,
  ⟨401, .tag, 1794614400000000, 1, 52, 233⟩,
  ⟨400, .tag, 1794614400000000, 1, 52, 231⟩,
  ⟨251, .fileModified, 1422046030000000, 2000000, 92, 69⟩,
  ⟨413, .tag, 1794614400000000, 1, 92, 233⟩,
  ⟨108, .fileCreated, 1427205567120000, 10000, 92, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := .both (Sets.fileModifiedAt 248) (.both (Sets.tagged 248 .obj 430 233) (.both (Sets.recoveredOnDevice 127 500) (.both (Sets.fileModifiedAt 249) (.both (Sets.tagged 249 .obj 432 233) (.both (Sets.recoveredOnDevice 128 500) (.both (Sets.fileModifiedAt 250) (.both (Sets.tagged 250 .obj 401 233) (.both (Sets.tagged 250 .obj 400 231) (.both (Sets.fileModifiedAt 251) (.both (Sets.tagged 251 .obj 413 233) (Sets.recoveredOnDevice 108 499)))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M180

#print axioms Cert.M180.verified
