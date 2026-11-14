import ChainOfProof
open ChainOfProof

namespace Cert.A136

def cited : List Fact := [
  ⟨118, .fileCreated, 1427205606780000, 10000, 102, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := Sets.recoveredOnDevice 118 376

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A136

#print axioms Cert.A136.verified
