import ChainOfProof
open ChainOfProof

namespace Cert.A181

def cited : List Fact := [
  ⟨110, .fileCreated, 1427205579580000, 10000, 94, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := Sets.recoveredOnDevice 110 376

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A181

#print axioms Cert.A181.verified
