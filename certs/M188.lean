import ChainOfProof
open ChainOfProof

namespace Cert.M188

def cited : List Fact := [
  ⟨215, .fileModified, 1420473442000000, 1, 124, 111⟩,
  ⟨443, .tag, 1794614400000000, 1, 124, 241⟩,
  ⟨141, .fileCreated, 1427230519305016, 1, 124, 111⟩,
  ⟨500, .unallocatedOnDevice, 1794614400000000, 1, 249, 111⟩,
  ⟨216, .fileModified, 1420473442000000, 1, 125, 111⟩,
  ⟨446, .tag, 1794614400000000, 1, 125, 241⟩,
  ⟨142, .fileCreated, 1427230519305016, 1, 125, 111⟩,
  ⟨217, .fileModified, 1420473442000000, 2000000, 99, 69⟩,
  ⟨420, .tag, 1794614400000000, 1, 99, 241⟩,
  ⟨115, .fileCreated, 1427205583550000, 10000, 99, 69⟩,
  ⟨499, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := .both (Sets.fileModifiedAt 215) (.both (Sets.tagged 215 .obj 443 241) (.both (Sets.recoveredOnDevice 141 500) (.both (Sets.fileModifiedAt 216) (.both (Sets.tagged 216 .obj 446 241) (.both (Sets.recoveredOnDevice 142 500) (.both (Sets.fileModifiedAt 217) (.both (Sets.tagged 217 .obj 420 241) (Sets.recoveredOnDevice 115 499))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M188

#print axioms Cert.M188.verified
