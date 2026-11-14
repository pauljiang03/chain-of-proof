import ChainOfProof
open ChainOfProof

namespace Cert.A179

def cited : List Fact := [
  ⟨108, .fileCreated, 1427205567120000, 10000, 92, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩ ]

def claim : Claim := Sets.recoveredOnDevice 108 376

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A179

#print axioms Cert.A179.verified
