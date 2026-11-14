import ChainOfProof
open ChainOfProof

namespace Cert.A138

def cited : List Fact := [
  ⟨120, .fileCreated, 1427205612970000, 10000, 104, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := Sets.recoveredOnDevice 120 376

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A138

#print axioms Cert.A138.verified
