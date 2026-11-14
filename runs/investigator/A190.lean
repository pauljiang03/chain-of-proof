import ChainOfProof
open ChainOfProof

namespace Cert.A190

def cited : List Fact := [
  ⟨119, .fileCreated, 1427205612590000, 10000, 103, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := Sets.recoveredOnDevice 119 376

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A190

#print axioms Cert.A190.verified
