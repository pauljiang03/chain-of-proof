import ChainOfProof
open ChainOfProof

namespace Cert.M182

def cited : List Fact := [
  ⟨211, .fileModified, 1419018826000000, 1, 130, 111⟩,
  ⟨449, .tag, 1794614400000000, 1, 130, 235⟩,
  ⟨147, .fileCreated, 1427230540318253, 1, 130, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨212, .fileModified, 1419018826000000, 1, 131, 111⟩,
  ⟨451, .tag, 1794614400000000, 1, 131, 235⟩,
  ⟨148, .fileCreated, 1427230540318253, 1, 131, 111⟩,
  ⟨213, .fileModified, 1419018826000000, 10000, 18, 19⟩,
  ⟨406, .tag, 1794614400000000, 1, 18, 235⟩,
  ⟨405, .tag, 1794614400000000, 1, 18, 231⟩,
  ⟨214, .fileModified, 1419018826000000, 2000000, 102, 69⟩,
  ⟨423, .tag, 1794614400000000, 1, 102, 235⟩,
  ⟨118, .fileCreated, 1427205606780000, 10000, 102, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := .both (Sets.fileModifiedAt 211) (.both (Sets.tagged 211 .obj 449 235) (.both (Sets.recoveredOnDevice 147 500) (.both (Sets.fileModifiedAt 212) (.both (Sets.tagged 212 .obj 451 235) (.both (Sets.recoveredOnDevice 148 500) (.both (Sets.fileModifiedAt 213) (.both (Sets.tagged 213 .obj 406 235) (.both (Sets.tagged 213 .obj 405 231) (.both (Sets.fileModifiedAt 214) (.both (Sets.tagged 214 .obj 423 235) (Sets.recoveredOnDevice 118 499)))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M182

#print axioms Cert.M182.verified
