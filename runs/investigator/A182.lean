import ChainOfProof
open ChainOfProof

namespace Cert.A182

def cited : List Fact := [
  ⟨111, .fileCreated, 1427205579680000, 10000, 95, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := Sets.recoveredOnDevice 111 376

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A182

#print axioms Cert.A182.verified
