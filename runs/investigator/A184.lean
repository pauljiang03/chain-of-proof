import ChainOfProof
open ChainOfProof

namespace Cert.A184

def cited : List Fact := [
  ⟨113, .fileCreated, 1427205580710000, 10000, 97, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := Sets.recoveredOnDevice 113 376

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A184

#print axioms Cert.A184.verified
