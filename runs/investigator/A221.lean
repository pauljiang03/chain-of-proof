import ChainOfProof
open ChainOfProof

namespace Cert.A221

def cited : List Fact := [
  ⟨85, .fileCreated, 1427144117150000, 10000, 68, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := Sets.recoveredOnDevice 85 376

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A221

#print axioms Cert.A221.verified
