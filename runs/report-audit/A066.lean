import ChainOfProof
open ChainOfProof

namespace Cert.A066

def cited : List Fact := [
  ⟨164, .fileModified, 1419018826000000, 2000000, 102, 69⟩,
  ⟨342, .tag, 1794614400000000, 1, 102, 201⟩,
  ⟨163, .fileModified, 1419018826000000, 10000, 18, 19⟩,
  ⟨332, .tag, 1794614400000000, 1, 18, 201⟩,
  ⟨118, .fileCreated, 1427205606780000, 10000, 102, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := .both (Sets.tagged 164 .obj 342 201) (.both (Sets.tagged 163 .obj 332 201) (Sets.recoveredOnDevice 118 376))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A066

#print axioms Cert.A066.verified
