import ChainOfProof
open ChainOfProof

namespace Cert.M142

def cited : List Fact := [
  ⟨159, .fileModified, 1418746226000000, 10000, 51, 19⟩,
  ⟨325, .tag, 1794614400000000, 1, 51, 198⟩,
  ⟨324, .tag, 1794614400000000, 1, 51, 197⟩,
  ⟨160, .fileModified, 1418746226000000, 2000000, 93, 69⟩,
  ⟨340, .tag, 1794614400000000, 1, 93, 198⟩,
  ⟨109, .fileCreated, 1427205577630000, 10000, 93, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := .both (Sets.fileModifiedAt 159) (.both (Sets.tagged 159 .obj 325 198) (.both (Sets.tagged 159 .obj 324 197) (.both (Sets.fileModifiedAt 160) (.both (Sets.tagged 160 .obj 340 198) (Sets.recoveredOnDevice 109 376)))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M142

#print axioms Cert.M142.verified
