import ChainOfProof
open ChainOfProof

namespace Cert.A192

def cited : List Fact := [
  ⟨121, .fileCreated, 1427205613550000, 10000, 105, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := Sets.recoveredOnDevice 121 376

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A192

#print axioms Cert.A192.verified
