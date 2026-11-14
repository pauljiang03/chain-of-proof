import ChainOfProof
open ChainOfProof

namespace Cert.M191

def cited : List Fact := [
  ⟨218, .fileModified, 1420485308000000, 1, 133, 111⟩,
  ⟨453, .tag, 1794614400000000, 1, 133, 244⟩,
  ⟨150, .fileCreated, 1427230543859459, 1, 133, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨219, .fileModified, 1420485308000000, 1, 135, 111⟩,
  ⟨459, .tag, 1794614400000000, 1, 135, 244⟩,
  ⟨152, .fileCreated, 1427230543859459, 1, 135, 111⟩,
  ⟨220, .fileModified, 1420485308000000, 2000000, 104, 69⟩,
  ⟨425, .tag, 1794614400000000, 1, 104, 244⟩,
  ⟨120, .fileCreated, 1427205612970000, 10000, 104, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := .both (Sets.fileModifiedAt 218) (.both (Sets.tagged 218 .obj 453 244) (.both (Sets.recoveredOnDevice 150 500) (.both (Sets.fileModifiedAt 219) (.both (Sets.tagged 219 .obj 459 244) (.both (Sets.recoveredOnDevice 152 500) (.both (Sets.fileModifiedAt 220) (.both (Sets.tagged 220 .obj 425 244) (Sets.recoveredOnDevice 120 499))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M191

#print axioms Cert.M191.verified
