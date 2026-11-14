import ChainOfProof
open ChainOfProof

namespace Cert.A214

def cited : List Fact := [
  ⟨108, .fileCreated, 1427205567120000, 10000, 92, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨339, .tag, 1794614400000000, 1, 92, 199⟩,
  ⟨176, .fileModified, 1422046030000000, 10000, 52, 19⟩,
  ⟨327, .tag, 1794614400000000, 1, 52, 199⟩,
  ⟨326, .tag, 1794614400000000, 1, 52, 197⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 108 376) (.both (Sets.tagged 108 .obj 339 199) (.both (Sets.tagged 176 .obj 327 199) (Sets.tagged 176 .obj 326 197)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A214

#print axioms Cert.A214.verified
