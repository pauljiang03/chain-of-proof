import ChainOfProof
open ChainOfProof

namespace Cert.M143

def cited : List Fact := [
  ⟨176, .fileModified, 1422046030000000, 10000, 52, 19⟩,
  ⟨327, .tag, 1794614400000000, 1, 52, 199⟩,
  ⟨326, .tag, 1794614400000000, 1, 52, 197⟩,
  ⟨177, .fileModified, 1422046030000000, 2000000, 92, 69⟩,
  ⟨339, .tag, 1794614400000000, 1, 92, 199⟩,
  ⟨108, .fileCreated, 1427205567120000, 10000, 92, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := .both (Sets.fileModifiedAt 176) (.both (Sets.tagged 176 .obj 327 199) (.both (Sets.tagged 176 .obj 326 197) (.both (Sets.fileModifiedAt 177) (.both (Sets.tagged 177 .obj 339 199) (Sets.recoveredOnDevice 108 376)))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M143

#print axioms Cert.M143.verified
