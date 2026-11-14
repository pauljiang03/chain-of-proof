import ChainOfProof
open ChainOfProof

namespace Cert.A142

def cited : List Fact := [
  ⟨124, .fileCreated, 1427205618410000, 10000, 108, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := Sets.recoveredOnDevice 124 376

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A142

#print axioms Cert.A142.verified
