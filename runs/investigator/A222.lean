import ChainOfProof
open ChainOfProof

namespace Cert.A222

def cited : List Fact := [
  ⟨107, .fileCreated, 1427144137810000, 10000, 91, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := Sets.recoveredOnDevice 107 376

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A222

#print axioms Cert.A222.verified
