import ChainOfProof
open ChainOfProof

namespace Cert.A133

def cited : List Fact := [
  ⟨115, .fileCreated, 1427205583550000, 10000, 99, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := Sets.recoveredOnDevice 115 376

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A133

#print axioms Cert.A133.verified
