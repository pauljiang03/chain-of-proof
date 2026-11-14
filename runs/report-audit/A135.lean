import ChainOfProof
open ChainOfProof

namespace Cert.A135

def cited : List Fact := [
  ⟨117, .fileCreated, 1427205584860000, 10000, 101, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := Sets.recoveredOnDevice 117 376

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A135

#print axioms Cert.A135.verified
