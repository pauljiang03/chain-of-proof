import ChainOfProof
open ChainOfProof

namespace Cert.M179

def cited : List Fact := [
  ⟨203, .fileModified, 1418746226000000, 1, 34, 111⟩,
  ⟨431, .tag, 1794614400000000, 1, 34, 232⟩,
  ⟨129, .fileCreated, 1427230482676152, 1, 34, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨204, .fileModified, 1418746226000000, 1, 113, 111⟩,
  ⟨433, .tag, 1794614400000000, 1, 113, 232⟩,
  ⟨130, .fileCreated, 1427230482676152, 1, 113, 111⟩,
  ⟨205, .fileModified, 1418746226000000, 10000, 51, 19⟩,
  ⟨399, .tag, 1794614400000000, 1, 51, 232⟩,
  ⟨398, .tag, 1794614400000000, 1, 51, 231⟩,
  ⟨206, .fileModified, 1418746226000000, 2000000, 93, 69⟩,
  ⟨414, .tag, 1794614400000000, 1, 93, 232⟩,
  ⟨109, .fileCreated, 1427205577630000, 10000, 93, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := .both (Sets.fileModifiedAt 203) (.both (Sets.tagged 203 .obj 431 232) (.both (Sets.recoveredOnDevice 129 500) (.both (Sets.fileModifiedAt 204) (.both (Sets.tagged 204 .obj 433 232) (.both (Sets.recoveredOnDevice 130 500) (.both (Sets.fileModifiedAt 205) (.both (Sets.tagged 205 .obj 399 232) (.both (Sets.tagged 205 .obj 398 231) (.both (Sets.fileModifiedAt 206) (.both (Sets.tagged 206 .obj 414 232) (Sets.recoveredOnDevice 109 499)))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M179

#print axioms Cert.M179.verified
