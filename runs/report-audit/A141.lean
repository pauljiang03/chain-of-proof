import ChainOfProof
open ChainOfProof

namespace Cert.A141

def cited : List Fact := [
  ⟨123, .fileCreated, 1427205615650000, 10000, 107, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := Sets.recoveredOnDevice 123 376

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A141

#print axioms Cert.A141.verified
